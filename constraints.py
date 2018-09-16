
from utils import group_task_by_time_overlap, group_task_by_scheduled_task, group_task_by_task, map_to_indicies, get_task_duration

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


    def add_same_worker_same_task_time(self, solver):
        """
            This constraint ensures workers cannot be assigned to at most one task at an point in time
        """
        grouped_task_time = map_to_indicies(group_task_by_time_overlap(self.tasks))

        [solver.Add(solver.Sum(self.assignments[i][j] for j in task_time_indexes) <= 1)
            for task_time_indexes in grouped_task_time
                for i in range(self.num_workers)]

    def worker_task_in_map(self, worker_id, task_id, map):
        if map == None:
            return False

        return worker_id in map and task_id in map[worker_id]

    def add_same_task_qty(self, solver, must_map, cannot_map):
        """
            This constraint ensures that workers assigned to tasks only one (1 / qty) and also obey forced must/cannot constraints
        """
        grouped_scheduled_task = group_task_by_scheduled_task(self.tasks)

        for i in range(self.num_workers):
            for task_scheduled_group in grouped_scheduled_task:
                # Each group will have same task, so use first one to get id
                task_index = task_scheduled_group[0].index
                worker_task = self.assignments_ref[i][task_index]

                worker_id_str = str(worker_task.worker['id'])
                task_id_str = str(worker_task.task.task_id)

                # if in must work, sum for task qty for use has to be 1
                if self.worker_task_in_map(worker_id_str, task_id_str, must_map):
                    solver.Add(solver.Sum(self.assignments[i][task.index] for task in task_scheduled_group) == 1)
                # if in cannot work, sum for task qty for use has to be 0
                elif self.worker_task_in_map(worker_id_str, task_id_str, cannot_map):
                    solver.Add(solver.Sum(self.assignments[i][task.index] for task in task_scheduled_group) == 0)
                # otherwise can be either
                else:
                    solver.Add(solver.Sum(self.assignments[i][task.index] for task in task_scheduled_group) <= 1)

    def add_at_least_work_task(self, solver, at_least_map):
        """
            This constraint ensures that workers work at least on task in the given map
        """
        grouped_task = group_task_by_task(self.tasks)

        for i in range(self.num_workers):
            for task_group in grouped_task:
                # Each group will have same task, so use first one to get id
                task_index = task_group[0].index
                worker_task = self.assignments_ref[i][task_index]

                worker_id_str = str(worker_task.worker['id'])
                task_id_str = str(worker_task.task.task_id)

                if self.worker_task_in_map(worker_id_str, task_id_str, at_least_map):
                    solver.Add(solver.Sum(self.assignments[i][task.index] for task in task_group) == 1)

    def add_time_fatigue_total(self, solver, fatigue_total_map):
        """
            This constraint ensures that no worker can work more than a given limit for any number of tasks
        """
        grouped_scheduled_task = group_task_by_scheduled_task(self.tasks)

        for i in range(self.num_workers):
            for task_scheduled_group in grouped_scheduled_task:
                # Each group will have same task, so use first one to get id
                task_index = task_scheduled_group[0].index
                worker_task = self.assignments_ref[i][task_index]

                worker_id_str = str(worker_task.worker['id'])
                task_id_str = str(worker_task.task.task_id)

                # if worker and task have time limit, add constraints
                if worker_id_str in fatigue_total_map:
                    worker_total_fatigue_constraints = fatigue_total_map[worker_id_str]

                    # for every fatigue constraint, the decision var * time must be lower than limit
                    for total_fatigue in worker_total_fatigue_constraints:
                        limit = total_fatigue['limit']
                        tasks_for_limit = total_fatigue['tasks']

                        solver.Add(
                            solver.Sum(
                                self.assignments[i][task.index] * get_task_duration(task)
                                    for task in task_scheduled_group
                                        if task.task_id in tasks_for_limit) <= limit)


    def add_overall_total_fatigue_time(self, solver, overall_map):
        """
            This constraint ensures workers work below a given limit overall for all their allocated tasks
        """
        for i in range(self.num_workers):
            worker = self.workers[i]
            worker_id_str = str(worker['id'])
            if worker_id_str in overall_map:
                limit = overall_map[worker_id_str]['limit']
                for j in range(self.num_workers):
                    print(get_task_duration(self.assignments_ref[i][j].task))
                solver.Add(
                    solver.Sum(self.assignments[i][j] * get_task_duration(self.assignments_ref[i][j].task)
                        for j in range(self.num_tasks)) <= limit)
