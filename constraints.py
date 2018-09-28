import utils

class Constraints():
    def __init__(
        self,
        tasks,
        workers,
        assignment_costs,
        assignments,
        assignments_ref,
    ):
        self.tasks = tasks
        self.workers = workers
        self.num_tasks = len(tasks)
        self.num_workers = len(workers)
        self.assignment_costs = assignment_costs
        self.assignments = assignments
        self.assignments_ref = assignments_ref

    def addOneWorkerOneTask(self, solver):
        [solver.Add(solver.Sum(self.assignments[i][j]
            for i in range(self.num_workers)) == 1)
                for j in range(self.num_tasks)]


    def add_task_qty_constraint(self, solver):
        [solver.Add(solver.Sum(self.assignments[i][j]
            for i in range(self.num_workers)) == self.tasks[j].qty)
                for j in range(self.num_tasks)]

    def add_same_worker_same_task_time(self, solver):
        """
            This constraint ensures workers cannot be assigned to at most one task at an point in time
        """
        grouped_task_time = utils.map_to_indicies(utils.group_task_by_time_overlap(self.tasks))

        [solver.Add(solver.Sum(self.assignments[i][j] for j in task_time_indexes) <= 1)
            for task_time_indexes in grouped_task_time
                for i in range(self.num_workers)]

    def worker_task_in_map(self, worker_id, task_id, map):
        if map == None:
            return False

        return worker_id in map and task_id in map[worker_id]

    def must_cannot_work(self, solver, must_map, cannot_map):
        """
            This constraint ensures that workers obey forced must/cannot constraints
        """
        for i in range(self.num_workers):
            for j in range(self.num_tasks):
                worker_task = self.assignments_ref[i][j]

                worker_id_str = str(worker_task.worker.id)
                task_id_str = str(worker_task.task.task_id)

                # if in must work, sum for task qty for use has to be 1
                if self.worker_task_in_map(worker_id_str, task_id_str, must_map):
                    solver.Add(self.assignments[i][j] == 1)
                # if in cannot work, sum for task qty for use has to be 0
                elif self.worker_task_in_map(worker_id_str, task_id_str, cannot_map):
                    solver.Add(self.assignments[i][j] == 0)

    def add_at_least_work_task(self, solver, at_least_map):
        """
            This constraint ensures that workers work at least on task in the given map
        """
        grouped_task = utils.group_task_by_task(self.tasks)

        for i in range(self.num_workers):
            for task_group in grouped_task:
                # Each group will have same task, so use first one to get id
                task_id_str = str(task_group[0].task_id)
                worker_id_str = str(self.workers[i].id)

                if self.worker_task_in_map(worker_id_str, task_id_str, at_least_map):
                    solver.Add(solver.Sum(self.assignments[i][task.index] for task in task_group) >= 1)

    def add_time_fatigue_total(self, solver, fatigue_total_map):
        """
            This constraint ensures that no worker can work more than a given limit for any number of tasks
        """
        for i in range(self.num_workers):
            worker_id_str = str(self.workers[i].id)

            # if worker and task have time limit, add constraints
            if worker_id_str in fatigue_total_map:
                worker_total_fatigue_constraints = fatigue_total_map[worker_id_str]

                # for every fatigue constraint, the decision var * time must be lower than limit
                for total_fatigue in worker_total_fatigue_constraints:
                    limit = total_fatigue['limit']
                    task_ids_for_limit = total_fatigue['tasks']
                    tasks_for_limit = [utils.findSchTaskByTaskId(id, self.tasks) for id in task_ids_for_limit]

                    for task_for_limit in tasks_for_limit:
                        solver.Add(
                            solver.Sum(
                                self.assignments[i][task.index] * utils.get_task_duration(task)
                                    for task in self.tasks if
                                        (task_for_limit != None and task.task_id == task_for_limit.task_id)
                                    ) <= limit)


    def add_overall_total_fatigue_time(self, solver, overall_map):
        """
            This constraint ensures workers work below a given limit overall for all their allocated tasks
            overall_map : { [worker_id] : { limit : number } }
        """
        for i in range(self.num_workers):
            worker = self.workers[i]
            worker_id_str = str(worker.index)
            if worker_id_str in overall_map:
                limit = overall_map[worker_id_str]['limit']
                solver.Add(
                    solver.Sum(self.assignments[i][j] * utils.get_task_duration(self.assignments_ref[i][j].task)
                        for j in range(self.num_tasks)) <= limit)


    def add_overall_consecutive_total_fatigue_time(self, solver, overall_consecutive_map):
        """
            This constraint ensures that workers can not consecutively work more than limit given in overall_consecutive_map
            overall_consecutive_map : { [limit] : worker_ids[] }
        """
        # Note: consecutive_map grouped by limit (15min increments) to reduce duplicate calculations

        for limit_str, limit_info in overall_consecutive_map.items():
            limit = int(limit_str)
            break_time = limit_info['breakTime']
            workers = limit_info['workers']

            # split tasks into ones that have duration over limit
            tasks_below_limit, tasks_over_limit = utils.split_task_by_duration_limit(self.tasks, limit)

            # Add constraints for each worker for limit
            for worker_id in workers:
                worker_index = utils.findWorkerById(worker_id, self.workers).index
                # Add cannot constraint to tasks_over_limit
                [solver.Add(self.assignments[worker_index][t.index] == 0) for t in tasks_over_limit]

                # For tasks lower, find all possible consecutive paths greater than limit
                consecutive_paths = utils.find_all_consecutive_paths(tasks_below_limit, limit)

                # Add constraint so that all tasks in a path cannot be assigned to worker
                for path in consecutive_paths:
                    solver.Add(solver.Sum(self.assignments[worker_index][t.index] for t in path.path_tasks) < len(path.path_tasks))

                    # for any path that is equal to the limit, ensure that break before next task is >= limit
                    if path.total_time == limit:
                        tasks_start_within_break_time_limit = utils.get_tasks_within_break_time_limit(
                            break_time,
                            path,
                            self.tasks
                        )

                        for task in tasks_start_within_break_time_limit:
                            solver.Add(self.assignments[worker_index][task.index] == 0)


    def add_unavailability(self, solver, unavailability_map):
        """
            This constraint ensures that workers cannot work scheduled tasks within given time spans
            unavailability_map : { [worker_id]: { range: { start_time, end_time } } }
        """
        for worker in self.workers:
            if str(worker.id) in unavailability_map:
                range = utils.get_range(unavailability_map[str(worker.id)]['range'])
                tasks_in_range = utils.get_tasks_in_range(self.tasks, range)

                for task in tasks_in_range:
                    solver.Add(self.assignments[worker.index][task.index] == 0)


    def add_buddy(self, solver, buddy_map):
        """
            This constraint ensures groups of workers work together on tasks.
            buddy_map : { [task_id] : worker_id[] }
        """

        for task in self.tasks:
            if str(task.task_id) in buddy_map:
                worker_buddies = buddy_map[str(task.task_id)]
                worker_buddy_indexes = [utils.findWorkerById(worker_id, self.workers).index for worker_id in worker_buddies]

                num_of_workers = len(worker_buddy_indexes)

                if num_of_workers > 1:
                    for index, i in enumerate(worker_buddy_indexes):
                        if index < num_of_workers - 1:
                            solver.Add(self.assignments[i][task.index] == self.assignments[worker_buddy_indexes[index + 1]][task.index])

    def add_nemesis(self, solver, nemesis_map):
        """
            This constraint ensures groups of workers can never work together in given tasks.
            nemesis_map : { [task_id] : worker_id[] }
        """

        for task in self.tasks:
            if str(task.task_id) in nemesis_map:
                worker_nemesis = nemesis_map[str(task.task_id)]
                worker_nemesis_indexes = [utils.findWorkerById(worker_id, self.workers).index for worker_id in worker_nemesis]

                solver.Add(solver.Sum(self.assignments[i][task.index] for i in worker_nemesis_indexes) <= 1)
