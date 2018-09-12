
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


    def addSameWorkerSameTaskTime(self, solver):
        grouped_task_time = map_to_indicies(group_task_by_time_overlap(self.tasks))

        [solver.Add(solver.Sum(self.assignments[i][j] for j in task_time_indexes) <= 1)
            for task_time_indexes in grouped_task_time
                for i in range(self.num_workers)]

    def addSameTaskQtyOnce(self, solver):
        grouped_scheduled_task = map_to_indicies(group_task_by_scheduled_task(self.tasks))

        [solver.Add(solver.Sum(self.assignments[i][j] for j in task_scheduled_indexes) <= 1)
            for task_scheduled_indexes in grouped_scheduled_task
            for i in range(self.num_workers)]

    def mustOrCannotWorkTask(self, solver, must_work_constraint, var_value):
        for i, worker_tasks in enumerate(self.assignments_ref):
            for j, worker_task in enumerate(worker_tasks):
                [solver.Add(self.assignments[i][j] == var_value)
                    for c in must_work_constraint
                        if c['workerId'] == worker_task.worker['id']
                        and c['taskId'] == worker_task.task.task_id]
