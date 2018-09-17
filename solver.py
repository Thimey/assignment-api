import json

from collections import namedtuple
from ortools.constraint_solver import pywrapcp



from utils import same_time, group_task_by_time_overlap, group_task_by_scheduled_task, map_to_indicies, map_to_id
from constraints import Constraints

Task = namedtuple('Task', ['id', 'task_id', 'qty', 'start_time', 'end_time', 'index'])
Worker_task = namedtuple('Worker_task', ['worker', 'task', 'index'])

min_num_allocations_per_worker = 3

class SearchMonitor(pywrapcp.SearchMonitor):
    def __init__(self, solver, assignments, num_tasks, num_workers):
        pywrapcp.SearchMonitor.__init__(self, solver)
        self.assignments = assignments
        self.num_tasks = num_tasks
        self.num_workers = num_workers


    def AcceptSolution(self):
        print('Accepting solution')
        assignment_vals = [self.assignments[i][j].Value() for i in range(self.num_workers) for j in range(self.num_tasks)]

        print('assignment_vals', assignment_vals)

        return True

    def AcceptDelta(self, delta):
        print('delta', delta)

        return True

def solver(data):
    # initialise solver
    solver = pywrapcp.Solver("allocations")

    tasks = get_tasks(data['scheduledTasks'])
    cost_matrix = data['costMatrix']
    workers = data['workers']
    solver_option = data['solverOption']
    time_limit = data['timeLimit']
    extra_constraints = data['constraints'] if 'constraints' in data else {}

    print('solver_option', solver_option)

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

    constraints = Constraints(
        tasks,
        workers,
        assignment_costs,
        assignments,
        assignments_ref,
    )

    # objective

    total_cost = solver.IntVar(0, 1000, "total_cost")

    solver.Add(
        total_cost == solver.Sum(
            [assignment_costs[i][j] * assignments[i][j] for i in range(num_workers) for j in range(num_tasks)]))

    # Only add objective if optimisation requested
    if solver_option != 'noOptimisation':
        objective = solver.Minimize(total_cost, 1)

    # constraints

    # each task assigned it's given qty
    constraints.addTaskQtyConstraint(solver)

    # a worker cannot work on two tasks that are on at the same time
    constraints.add_same_worker_same_task_time(solver)

    # a worker can at most be assigned to the same orderTask date once (i.e cannot take up multiple qty)
    # maybe add any cannot work constraints
    # maybe add any must work constraints
    must_map = extra_constraints['mustWork'] if 'mustWork' in extra_constraints else None
    cannot_map = extra_constraints['cannotWork'] if 'cannotWork' in extra_constraints else None
    constraints.add_same_task_qty(solver, must_map, cannot_map)

    # add at least has to work constraint
    if 'atLeastWork' in extra_constraints:
        constraints.add_at_least_work_task(solver, extra_constraints['atLeastWork'])

    # add total time fatigue constraints
    if 'timeFatigueTotal' in extra_constraints:
        constraints.add_time_fatigue_total(solver, extra_constraints['timeFatigueTotal'])

    # add total overall time fatigue constraints
    if 'overallTimeFatigueTotal' in extra_constraints:
        constraints.add_overall_total_fatigue_time(solver, extra_constraints['overallTimeFatigueTotal'])

    # add consecutive fatigue constaints

    # add unavailable time constraints

    # works must be assigned to at least n tasks (this could change later per worker)
    # [solver.Add(solver.Sum(assignments[i][j] for j in range(num_tasks)) >= 3) for i in range(num_workers)]


    # Create the decision builder.
    assignments_flat = [assignments[i][j] for i in range(num_workers) for j in range(num_tasks)]

    db = solver.Phase(
        assignments_flat,
        solver.CHOOSE_MIN_SIZE_LOWEST_MIN,
        solver.ASSIGN_MIN_VALUE
    )

    # Create solution collector depending on solver option requested
    if solver_option != 'noOptimisation':
        collector = solver.BestValueSolutionCollector(False)
    else:
        collector = solver.FirstSolutionCollector()

    # Add decision vars to collector
    collector.Add(assignments_flat)

    # Set time limit if given
    if solver_option == 'optimise' and time_limit != None:
        print('time_limit', time_limit)
        solver_time_limit = solver.TimeLimit(time_limit * 60 * 1000)

    # Search monitor
    monitor = SearchMonitor(solver, assignments, num_tasks, num_workers)

    # Solve appropriately
    if solver_option == 'optimal':
        collector.AddObjective(total_cost)
        status = solver.Solve(db, [objective, collector])
    elif solver_option == 'optimise' and time_limit != None:
        collector.AddObjective(total_cost)
        status = solver.Solve(db, [objective, collector, solver_time_limit])
    else:
        status = solver.Solve(db, [collector, monitor])

    print("Time:", solver.WallTime(), "ms")
    print('status', status)

    # If solution found, collect all assignments
    if status:
        solution_by_task = {}
        solution_by_worker = {}
        for i in range(num_workers):
            for j in range(num_tasks):
                if collector.Value(0, assignments[i][j]) == 1:
                    workerTask = assignments_ref[i][j]
                    # Group solution by worker and task

                    if workerTask.task.id in solution_by_task:
                        solution_by_task[workerTask.task.id] = [*solution_by_task[workerTask.task.id], workerTask.worker['id']]
                    else:
                        solution_by_task[workerTask.task.id] = [workerTask.worker['id']]

                    if workerTask.worker['id'] in solution_by_worker:
                        solution_by_worker[workerTask.worker['id']] = [*solution_by_worker[workerTask.worker['id']], workerTask.task.id]
                    else:
                        solution_by_worker[workerTask.worker['id']] = [workerTask.task.id]

        objective_value = get_non_optimised_cost(cost_matrix, solution_by_task) if solver_option == 'noOptimisation' else collector.ObjectiveValue(0)

        return {
            "status": status,
            "solutionByTask": solution_by_task,
            "solutionByWorker": solution_by_worker,
            "objectiveValue": objective_value
        }

    return {
        "status": status,
        "solutionByTask": None,
        "solutionByWorker": None,
        "objectiveValue": None
    }


def assemble_solution():
    pass

def get_tasks(scheduled_tasks):
    tasks = []
    index = 0
    for scheduled_task in scheduled_tasks:
        tasks.append(
            Task(
                scheduled_task['id'],
                scheduled_task['task']['id'],
                scheduled_task['task']['qty'],
                scheduled_task['startTime'],
                scheduled_task['endTime'],
                index
            )
        )
        index += 1

    return tasks

def get_non_optimised_cost(cost_matrix, solution):
    total = 0

    for task_id, workers in solution.items():
        task_cost = 0
        for worker_id in workers:
            task_cost += cost_matrix[str(worker_id)][task_id]
        total += task_cost

    return total


def get_data(file_path):
    data_file = open(file_path, 'r')
    data = json.load(data_file)
    data_file.close()

    return data

if __name__ == "__main__":
    solver(get_data('./data.json'))