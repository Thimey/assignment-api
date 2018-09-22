from collections import namedtuple

def time_in_mins(time):
    return (time['hour'] * 60) + time['min']

def time_in_range(time, start_range, end_range):
    return (time_in_mins(start_range) < time_in_mins(time) < time_in_mins(end_range))

def exactly_same_range(task1, task2):
    return (
        time_in_mins(task1.start_time) == time_in_mins(task2.start_time) and
        time_in_mins(task1.end_time) == time_in_mins(task2.end_time)
    )

def same_time(task1, task2):
    return (
        exactly_same_range(task1, task2) or
        time_in_range(task1.start_time, task2.start_time, task2.end_time) or
        time_in_range(task1.end_time, task2.start_time, task2.end_time) or
        time_in_range(task2.start_time, task1.start_time, task1.end_time) or
        time_in_range(task2.end_time, task1.start_time, task1.end_time)
    )

def get_task_duration(task):
    return (
        time_in_mins(task.end_time) - time_in_mins(task.start_time)
    )

def split_task_by_duration_limit(tasks, limit):
    over = []
    under = []
    for task in tasks:
        if get_task_duration(task) > limit:
            over.append(task)
        else:
            under.append(task)

    return (under, over)

# def group_tasks(tasks, predicate):
#     grouped_tasks = [[t] for t in tasks]
#     for index, task_group in enumerate(grouped_tasks):
#         for task in tasks:
#             # First one is base, dont compare itself
#             head, *tail = task_group
#             if task != head and predicate(task, task_group):
#                 grouped_tasks[index] = [*task_group, task]

#     # remove any groups with only one task
#     return [g for g in grouped_tasks if len(g) > 1]


def already_have(potential, groups):
    for g in groups:
        if set([t.id for t in g]) == set([t.id for t in potential]):
            return True

    return False



def group_tasks(tasks, predicate):
    grouped_tasks = [[t] for t in tasks]
    for task in tasks:
        for index, task_group in enumerate(grouped_tasks):
            if task not in task_group and predicate(task, task_group):
                new_group = [*task_group, task]
                if not already_have(new_group, grouped_tasks):
                    grouped_tasks.append(new_group)

    # remove any groups with only one task
    return [g for g in grouped_tasks if len(g) > 1]


def all_tasks_share_scheduled_id(task, tasks):
    return all([t.id == task.id for t in tasks])

def all_tasks_share_task_id(task, tasks):
    return all([t.task_id == task.task_id for t in tasks])

def all_tasks_share_time(task, tasks):
    return all([same_time(t, task) for t in tasks])

def group_task_by_time_overlap(tasks):
    return group_tasks(tasks, all_tasks_share_time)

def group_task_by_task(tasks):
    grouped_tasks = {}
    for task in tasks:
        if task.task_id in grouped_tasks:
            grouped_tasks[task.task_id] = [*grouped_tasks[task.task_id], task]
        else:
            grouped_tasks[task.task_id] = [task]

    return grouped_tasks.values()

def map_to_indicies(task_groups):
    return [[t.index for t in tg] for tg in task_groups]

def map_to_id(task_groups):
    return [[t.id for t in tg] for tg in task_groups]

def findSchTaskByTaskId(id, seq):
    return find(lambda t: t.task_id == id, seq)

def findWorkerById(id, seq):
    return find(lambda w: int(w.id) == int(id), seq)

def find(f, seq):
    """Return first item in sequence where f(item) == True."""
    for item in seq:
        if f(item):
            return item

    return None

def remove_by_id(items, id):
    new_items = []
    for item in items:
        if item.id != id:
            new_items.append(item)

    return new_items

def get_total_consecutive_time(time, task):
    return time + get_task_duration(task)

def end_task_of_path(tasks):
    length = len(tasks)

    if length:
        return tasks[length - 1]
    else:
        None

def tasks_connect(task1, task2):
    return time_in_mins(task1.end_time) == time_in_mins(task2.start_time)

Path = namedtuple('Path', ['total_time', 'path_tasks'])

def consecutive_tasks_until_limit(initial_task, tasks_after, limit):
    completed_paths = []
    potential_paths = [
        Path(get_task_duration(initial_task), [initial_task])
    ]
    new_path_created = True
    remaining_tasks = tasks_after[:]

    # if an all remaining tasks do not patch any paths, stop!
    while new_path_created:
        new_path_created = False
        new_remaining_tasks = remaining_tasks[:]
        for task_index, task in enumerate(remaining_tasks):
            new_potential_paths = potential_paths[:]
            # test if each remaining task can join a path
            for (total_time, path_tasks) in potential_paths:
                end_task = end_task_of_path(path_tasks)

                if tasks_connect(end_task, task):
                    new_time = get_total_consecutive_time(total_time, task)
                    new_path = Path(new_time, [*path_tasks, task])

                    if new_time >= limit:
                        # Add to completed
                        completed_paths.append(new_path)
                    else:
                        # Add to a potential path
                        new_potential_paths.append(new_path)
                        new_path_created = True

                    # Once a task connects to a path (completed or not), remove task so don't check again
                    new_remaining_tasks = remove_by_id(new_remaining_tasks, task.id)

            # update potential_paths
            potential_paths = new_potential_paths[:]

        remaining_tasks = new_remaining_tasks[:]

    return [path.path_tasks for path in completed_paths]




def find_all_consecutive_paths(tasks, limit):
    task_paths = []
    # sort by start time
    tasks_by_start = tasks[:]
    tasks_by_start.sort(key= lambda t: time_in_mins(t.start_time))

    for index, task in enumerate(tasks_by_start):
        # get all consecutive tasks from this task until limit
        tasks_after = tasks_by_start[index:len(tasks_by_start)]
        paths_from_task = consecutive_tasks_until_limit(task, tasks_after, limit)

        if len(paths_from_task):
            task_paths.append(paths_from_task)

    return task_paths


if __name__ == '__main__':
    Task = namedtuple('Task', ['id', 'start_time', 'end_time'])

    tasks = [
        Task(1, { "hour": 9, "min": 00 }, { "hour": 9, "min": 15 }),
        Task(2, { "hour": 9, "min": 15 }, { "hour": 9, "min": 30 }),
        Task(3, { "hour": 9, "min": 15 }, { "hour": 9, "min": 30 }),
        Task(4, { "hour": 10, "min": 15 }, { "hour": 9, "min": 30 }),
        Task(5, { "hour": 9, "min": 00 }, { "hour": 9, "min": 30 }),
        Task(6, { "hour": 9, "min": 15 }, { "hour": 10, "min": 00 }),
    ]

    paths = find_all_consecutive_paths(tasks, 45)

    print(paths)