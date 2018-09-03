import json

from collections import namedtuple
from ortools.constraint_solver import pywrapcp

from utils import same_time, group_task_by_time_overlap, group_task_by_scheduled_task, map_to_indicies, map_to_id

Task = namedtuple('Task', ['id', 'task_id', 'qty_n', 'start_time', 'end_time', 'index'])
Worker_task = namedtuple('Worker_task', ['worker', 'task', 'index'])

min_num_allocations_per_worker = 3

def solver(data):
    # initialise solver
    solver = pywrapcp.Solver("allocations")

    tasks = get_tasks(data['scheduledTasks'])
    cost_matrix = data['costMatrix']
    workers = data['workers']

    num_tasks = len(tasks)
    num_workers = len(workers)

    # declare decision variables and a reference matrix
    assignment_costs = []
    assignments = []
    assignments_ref = []
    for index, worker in enumerate(workers):
        worker_assignments = []
        worker_assignments_ref = []
        worker_assignment_costs = []
        for task in tasks:
            worker_assignments.append(solver.IntVar(0, 1, f'worker: , task: {task.id}'))
            worker_assignments_ref.append(Worker_task(worker, task, index))
            worker_assignment_costs.append(cost_matrix[str(worker['id'])][task.id])
        assignments.append(worker_assignments)
        assignments_ref.append(worker_assignments_ref)
        assignment_costs.append(worker_assignment_costs)


    # objective
    total_cost = solver.IntVar(0, 1000, "total_cost")

    solver.Add(
        total_cost == solver.Sum(
            [assignment_costs[i][j] * assignments[i][j] for i in range(num_workers) for j in range(num_tasks)]))

    objective = solver.Minimize(total_cost, 1)

    # constraints

    # each task assigned to exactly one worker
    [solver.Add(solver.Sum(assignments[i][j] for i in range(num_workers)) == 1) for j in range(num_tasks)]

    # works must be assigned to at least n tasks (this could change later per worker)
    # [solver.Add(solver.Sum(assignments[i][j] for j in range(num_tasks)) >= 3) for i in range(num_workers)]

    # a worker cannot work on two tasks that are on at the same time
    grouped_task_time = map_to_indicies(group_task_by_time_overlap(tasks))

    [solver.Add(solver.Sum(assignments[i][j] for j in task_time_indexes) <= 1)
    for task_time_indexes in grouped_task_time
    for i in range(num_workers)]

    # a worker can at most be assigned to the same orderTask date once (i.e cannot take up multiple qty)
    grouped_scheduled_task = map_to_indicies(group_task_by_scheduled_task(tasks))

    [solver.Add(solver.Sum(assignments[i][j] for j in task_scheduled_indexes) <= 1)
    for task_scheduled_indexes in grouped_scheduled_task
    for i in range(num_workers)]

    assignments_flat = [assignments[i][j] for i in range(num_workers) for j in range(num_tasks)]

    # Create the decision builder.
    db = solver.Phase(
        assignments_flat,
        solver.CHOOSE_FIRST_UNBOUND,
        solver.ASSIGN_MIN_VALUE
    )

    # Create solution collector
    collector = solver.BestValueSolutionCollector(False)
    collector.Add(assignments_flat)
    collector.AddObjective(total_cost)

    status = solver.Solve(db, [objective, collector])
    print("Time:", solver.WallTime(), "ms")
    print('status', status)

    # If solution found, collect all assignments
    if status:
        solution = {}
        for i in range(num_workers):
            for j in range(num_tasks):
                if collector.Value(0, assignments[i][j]) == 1:
                    workerTask = assignments_ref[i][j]
                    if workerTask.task.id in solution:
                        solution[workerTask.task.id] = [*solution[workerTask.task.id], workerTask.worker['id']]
                    else:
                        solution[workerTask.task.id] = [workerTask.worker['id']]

        return {
            "status": status,
            "solution": solution
        }

    return {
        "status": status,
        "solution": None
    }


def assemble_solution():
    pass

def get_tasks(scheduled_tasks):
    tasks = []
    index = 0
    for scheduled_task in scheduled_tasks:
        for qty in range(1, scheduled_task['task']['qty'] + 1):
            tasks.append(
                Task(
                    scheduled_task['id'],
                    scheduled_task['task']['id'],
                    qty,
                    scheduled_task['startTime'],
                    scheduled_task['endTime'],
                    index
                )
            )
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
    solver(get_data('./data.json'))