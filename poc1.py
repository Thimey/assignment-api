import json

from collections import namedtuple
from ortools.constraint_solver import pywrapcp

Task = namedtuple('Task', ['id', 'qty_n', 'date', 'index'])
Worker_task = namedtuple('Worker_task', ['worker', 'task', 'index'])

min_num_allocations_per_worker = 3

def main():
    # load data to allocate
    data = get_data('./data.json')

    # initialise solver
    solver = pywrapcp.Solver("allocations")

    tasks = get_tasks(data['orderTasks'])
    workers = data['workers']

    num_tasks = len(tasks)
    num_workers = len(workers)

    # declare decision variables and a reference matrix
    assignments = []
    assignments_ref = []
    for index, worker in enumerate(workers):
        worker_assignments = []
        worker_assignments_ref = []
        for task in tasks:
            worker_assignments.append(solver.IntVar(0, 1, f'worker: , task: {task.id}'))
            worker_assignments_ref.append(Worker_task(worker, task, index))
        assignments.append(worker_assignments)
        assignments_ref.append(worker_assignments_ref)

    # constraints

    # each task assigned to exactly one worker
    [solver.Add(solver.Sum(assignments[i][j] for i in range(num_workers)) == 1) for j in range(num_tasks)]

    # works must be assigned to at least n tasks (this could change later per worker)
    # [solver.Add(solver.Sum(assignments[i][j] for j in range(num_tasks)) >= 3) for i in range(num_workers)]

    # a worker cannot work on two tasks that are on the same day
    get_group_task_date = get_group_task_fn(lambda t: t.date)
    grouped_task_date = get_group_task_date(tasks)

    [solver.Add(solver.Sum(assignments[i][j] for j in task_date_indicies) <= 1)
    for task_date_indicies in grouped_task_date
    for i in range(num_workers)]

    # a worker can at most be assigned to the same orderTask date once (i.e cannot take up multiple qty)
    get_group_task_date_id = get_group_task_fn(lambda t: f'{str(t.id)}_{t.date}')
    grouped_task_date_id = get_group_task_date_id(tasks)

    [solver.Add(solver.Sum(assignments[i][j] for j in task_date_indicies) <= 1)
    for task_date_indicies in grouped_task_date_id
    for i in range(num_workers)]

    assignments_flat = [assignments[i][j] for i in range(num_workers) for j in range(num_tasks)]

    # Create the decision builder.
    db = solver.Phase(
        assignments_flat,
        solver.CHOOSE_FIRST_UNBOUND,
        solver.ASSIGN_MIN_VALUE
    )

    # Create solution colector
    collector = solver.FirstSolutionCollector()
    collector.Add(assignments_flat)

    status = solver.Solve(db, [collector])
    print("Time:", solver.WallTime(), "ms")
    print('status', status)

    if status:
        for i in range(num_workers):
            for j in range(num_tasks):
                if collector.Value(0, assignments[i][j]) == 1:
                    print('Worker ', i, ' assigned to task ', j)






def get_group_task_fn(group_fn):
    """
        returns a groupby function that groups in list of indicies list using supplied fn
    """
    def get_group_task(tasks):
        group_tasks = {}

        for task in tasks:
            key = group_fn(task)
            if key in group_tasks:
                group_tasks[key].append(task.index)
            else:
                group_tasks[key] = [task.index]

        return list(group_tasks.values())

    return get_group_task

def get_tasks(order_tasks):
    tasks = []
    index = 0
    for order_task in order_tasks:
        for qty in range(1, order_task['qty'] + 1):
            for date in order_task['dates']:
                tasks.append(Task(order_task['id'], qty, date, index))
                index += 1

    return tasks

def get_cost(worker, task):
    return 30

def get_data(file_path):
    data_file = open(file_path, 'r')
    data = json.load(data_file)
    data_file.close()

    return data

if __name__ == "__main__":
    main()