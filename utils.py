def time_in_mins(time):
    return (time['hour'] * 60) + time['min']

def time_in_range(time, start_range, end_range):
    return (time_in_mins(start_range) < time_in_mins(time) < time_in_mins(end_range))

def same_time(task1, task2):
    return (
        time_in_range(task1.start_time, task2.start_time, task2.end_time) or
        time_in_range(task1.end_time, task2.start_time, task2.end_time) or
        time_in_range(task2.start_time, task1.start_time, task1.end_time) or
        time_in_range(task2.end_time, task1.start_time, task1.end_time)
    )

def group_tasks(tasks, predicate):
    grouped_tasks = []
    for task in tasks:
        group_matched = False
        for index, task_group in enumerate(grouped_tasks):
            if predicate(task, task_group):
                group_matched = True
                grouped_tasks[index] = [*task_group, task]

        if not group_matched:
            grouped_tasks.append([task])

    return grouped_tasks


def all_tasks_share_scheduled_id(task, tasks):
    return all([t.id == task.id for t in tasks])

def all_tasks_share_time(task, tasks):
    return all([same_time(t, task) for t in tasks])

def group_task_by_time_overlap(tasks):
    return group_tasks(tasks, all_tasks_share_time)

def group_task_by_scheduled_task(tasks):
    return group_tasks(tasks, all_tasks_share_scheduled_id)

def map_to_indicies(task_groups):
    return [[t.index for t in tg] for tg in task_groups]