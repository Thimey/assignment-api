
from utils import same_time, group_task_by_time_overlap, group_task_by_scheduled_task, map_to_indicies, map_to_id

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
        grouped_task_time = map_to_indicies(group_task_by_time_overlap(self.tasks))

        [solver.Add(solver.Sum(self.assignments[i][j] for j in task_time_indexes) <= 1)
            for task_time_indexes in grouped_task_time
                for i in range(self.num_workers)]

    def worker_task_in_map(self, worker_id, task_id, map):
        if map == None:
            return False

        return str(worker_id) in map and str(task_id) in map[str(worker_id)]

    def add_same_task_qty(self, solver, must_map, cannot_map):
        grouped_scheduled_task = group_task_by_scheduled_task(self.tasks)

        for i in range(self.num_workers):
            for task_scheduled_group in grouped_scheduled_task:
                task_index = task_scheduled_group[0].index
                worker_task = self.assignments_ref[i][task_index]

                # if in must work, sum for task qty for use has to be 1
                if self.worker_task_in_map(worker_task.worker['id'], worker_task.task.task_id, must_map):
                    solver.Add(solver.Sum(self.assignments[i][task.index] for task in task_scheduled_group) == 1)
                # if in cannot work, sum for task qty for use has to be 0
                elif self.worker_task_in_map(worker_task.worker['id'], worker_task.task.task_id, cannot_map):
                    solver.Add(solver.Sum(self.assignments[i][task.index] for task in task_scheduled_group) == 0)
                # otherwise can be either
                else:
                    solver.Add(solver.Sum(self.assignments[i][task.index] for task in task_scheduled_group) <= 1)

