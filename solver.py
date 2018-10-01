import json

import copy
from collections import namedtuple
from ortools.constraint_solver import pywrapcp

import utils
from constraints import Constraints

Worker_task = namedtuple('Worker_task', ['worker', 'task'])

min_num_allocations_per_worker = 3

def solver(data):
    # initialise solver
    solver = pywrapcp.Solver("allocations")

    tasks = utils.get_tasks(data['scheduledTasks'])
    workers = utils.get_workers(data['workers'])

    cost_matrix = data['costMatrix']
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
    for worker in workers:
        worker_assignments = []
        worker_assignments_ref = []
        worker_assignment_costs = []
        for task in tasks:
            worker_assignments.append(solver.IntVar(0, 1, f'worker: , task: {task.id}'))
            worker_assignments_ref.append(Worker_task(worker, task))
            worker_assignment_costs.append(cost_matrix[str(worker.id)][task.id])
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


    # Only add objective if optimisation requested
    if solver_option != 'noOptimisation':
        total_cost = solver.IntVar(0, 3000, "total_cost")

        solver.Add(
            total_cost == solver.Sum(
                [assignment_costs[i][j] * assignments[i][j] for i in range(num_workers) for j in range(num_tasks)]))

        objective = solver.Minimize(total_cost, 5)

    # constraints

    # each task assigned it's given qty
    constraints.add_task_qty_constraint(solver)

    # a worker cannot work on two tasks that are on at the same time
    constraints.add_same_worker_same_task_time(solver)

    # a worker can at most be assigned to the same orderTask date once (i.e cannot take up multiple qty)
    # maybe add any cannot work constraints
    # maybe add any must work constraints
    must_map = extra_constraints['mustWork'] if 'mustWork' in extra_constraints else None
    cannot_map = extra_constraints['cannotWork'] if 'cannotWork' in extra_constraints else None
    constraints.must_cannot_work(solver, must_map, cannot_map)

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
    if 'overallTimeFatigueConsecutive' in extra_constraints:
        constraints.add_overall_consecutive_total_fatigue_time(solver, extra_constraints['overallTimeFatigueConsecutive'])

    # add unavailable time constraints
    if 'unavailable' in extra_constraints:
        constraints.add_unavailability(solver, extra_constraints['unavailable'])

    # add buddy constraints
    if 'buddy' in extra_constraints:
        constraints.add_buddy(solver, extra_constraints['buddy'])

    # add nemesis constraints
    if 'nemesis' in extra_constraints:
        constraints.add_nemesis(solver, extra_constraints['nemesis'])

    # works must be assigned to at least n tasks (this could change later per worker)
    # [solver.Add(solver.Sum(assignments[i][j] for j in range(num_tasks)) >= 3) for i in range(num_workers)]


    # Create the decision builder.

    # Want to sort the decision variables by least cost to the solution

    if solver_option != 'noOptimisation':
        assignment_ref_copy = copy.deepcopy(assignments_ref)
        assignment_ref_copy_flat = [assignment_ref_copy[i][j] for i in range(num_workers) for j in range(num_tasks)]
        # Sort by least cost
        assignment_ref_copy_flat.sort(key=lambda wrk_tsk: cost_matrix[str(wrk_tsk.worker.id)][wrk_tsk.task.id])
        # map to assignment vars
        assignments_flat = [assignments[ref.worker.index][ref.task.index] for ref in assignment_ref_copy_flat]
    else:
        assignments_flat = [assignments[i][j] for i in range(num_workers) for j in range(num_tasks)]

    db = solver.Phase(
        assignments_flat,
        solver.CHOOSE_FIRST_UNBOUND,
        solver.ASSIGN_MAX_VALUE
    )

    # Create solution collector depending on solver option requested
    if (solver_option == 'optimise' and time_limit != None) or solver_option == 'optimal':
        collector = solver.BestValueSolutionCollector(False) # False finds minimum as best solution
    else:
        collector = solver.FirstSolutionCollector()

    # Add decision vars to collector
    collector.Add(assignments_flat)

    monitor = pywrapcp.SearchMonitor(solver)

    monitor.RestartSearch()

    # Set time limit if given
    if solver_option == 'optimise' and time_limit != None:
        print('time_limit', time_limit)
        solver_time_limit = solver.TimeLimit(time_limit * 60 * 1000)

    # Solve appropriately
    if solver_option == 'optimal':
        collector.AddObjective(total_cost)
        status = solver.Solve(db, [objective, collector, monitor])
    elif solver_option == 'optimise' and time_limit != None:
        collector.AddObjective(total_cost)
        status = solver.Solve(db, [objective, collector, solver_time_limit, monitor])
    else:
        status = solver.Solve(db, [collector])

    print("Time:", solver.WallTime(), "ms")
    print('status', status)

    # If solution found, collect all assignments
    if status:
        solution_by_task = {}
        solution_by_worker = {}
        for i in range(num_workers):
            for j in range(num_tasks):
                if collector.Value(0, assignments[i][j]) == 1:
                    worker_task = assignments_ref[i][j]
                    # Group solution by worker and task

                    if worker_task.task.id in solution_by_task:
                        solution_by_task[worker_task.task.id] = [*solution_by_task[worker_task.task.id], worker_task.worker.id]
                    else:
                        solution_by_task[worker_task.task.id] = [worker_task.worker.id]

                    if worker_task.worker.id in solution_by_worker:
                        solution_by_worker[worker_task.worker.id] = [*solution_by_worker[worker_task.worker.id], worker_task.task.id]
                    else:
                        solution_by_worker[worker_task.worker.id] = [worker_task.task.id]

        if solver_option == 'optimal' or (solver_option == 'optimise' and time_limit != None):
            objective_value = collector.ObjectiveValue(0)
        else:
            objective_value = get_non_optimised_cost(cost_matrix, solution_by_task)

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