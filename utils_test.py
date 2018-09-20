import unittest
from utils import same_time, group_task_by_time_overlap, get_task_duration

from collections import namedtuple
Task = namedtuple('Task', ['id', 'start_time', 'end_time'])

class TestUtils(unittest.TestCase):
    def test_same_time(self):
        # Same time test
        self.assertEqual(
            same_time(
                Task('1', { "hour": 10, "min": 30 }, { "hour": 12, "min": 45 }),
                Task('2',{ "hour": 11, "min": 30 }, { "hour": 12, "min": 45 })
            ),
            True
        )

        self.assertEqual(
            same_time(
                Task('1', { "hour": 9, "min": 15 }, { "hour": 9, "min": 30 }),
                Task('2',{ "hour": 9, "min": 15 }, { "hour": 9, "min": 30 })
            ),
            True
        )

        # overlap
        self.assertEqual(
            same_time(
                Task('1', { "hour": 10, "min": 30 }, { "hour": 12, "min": 45 }),
                Task('1', { "hour": 12, "min": 45 }, { "hour": 14, "min": 45 })
            ),
            False
        )


    def test_group_task_by_time_overlap_1(self):
        task1 = Task('1', { "hour": 11, "min": 15 }, { "hour": 11, "min": 45 })
        task2 = Task('2', { "hour": 11, "min": 15 }, { "hour": 11, "min": 30 })
        task3 = Task('3', { "hour": 11, "min": 15 }, { "hour": 11, "min": 30 })
        task4 = Task('4', { "hour": 11, "min": 30 }, { "hour": 11, "min": 45 })

        expected_group = [
            [task1, task2, task3],
            [task1, task4],
        ]

        grouped = group_task_by_time_overlap([
            task1,
            task2,
            task3,
            task4,
        ])

        self.assertListEqual(expected_group, grouped)

    # def test_group_task_by_time_overlap_2(self):
    #     task1 = Task('1', { "hour": 9, "min": 15 }, { "hour": 9, "min": 30 })
    #     task2 = Task('2', { "hour": 9, "min": 15 }, { "hour": 9, "min": 45 })
    #     task3 = Task('3', { "hour": 9, "min": 30 }, { "hour": 9, "min": 45 })

    #     expected_group = [
    #         [task1, task2],
    #         [task2, task3]
    #     ]

    #     grouped = group_task_by_time_overlap([
    #         task1,
    #         task2,
    #         task3,
    #     ])

    #     self.assertListEqual(expected_group, grouped)


    # def test_group_task_by_time_overlap(self):
    #     task1 = Task('1', { "hour": 9, "min": 15 }, { "hour": 9, "min": 30 })
    #     task2 = Task('2', { "hour": 9, "min": 15 }, { "hour": 9, "min": 30 })
    #     task3 = Task('3', { "hour": 9, "min": 15 }, { "hour": 9, "min": 30 })
    #     task4 = Task('4', { "hour": 9, "min": 15 }, { "hour": 9, "min": 30 })
    #     task5 = Task('5', { "hour": 9, "min": 15 }, { "hour": 9, "min": 30 })

    #     expected_group = [
    #         [task1, task2, task3, task4, task5]
    #     ]

    #     grouped = group_task_by_time_overlap([
    #         task1,
    #         task2,
    #         task3,
    #         task4,
    #         task5,
    #     ])

    #     self.assertListEqual(expected_group, grouped)

    # def test_get_task_duration(self):
    #     task = Task('1', { "hour": 12, "min": 30 }, { "hour": 12, "min": 45 })
    #     task2 = Task('1', { "hour": 12, "min": 30 }, { "hour": 13, "min": 00 })

    #     duration1 = get_task_duration(task)
    #     duration2 = get_task_duration(task2)

    #     self.assertEqual(duration1, 15)
    #     self.assertEqual(duration2, 30)

    # def test_group_task_by_scheduled_task(self):
    #     task1 = Task('1', { "hour": 12, "min": 30 }, { "hour": 13, "min": 30 })
    #     task2 = Task('2', { "hour": 12, "min": 30 }, { "hour": 13, "min": 30 })
    #     task3 = Task('2', { "hour": 12, "min": 30 }, { "hour": 13, "min": 30 })
    #     task4 = Task('4', { "hour": 12, "min": 30 }, { "hour": 13, "min": 30 })
    #     task5 = Task('4', { "hour": 12, "min": 30 }, { "hour": 13, "min": 30 })

    #     expected_group = [
    #         [task1],
    #         [task2, task3],
    #         [task4, task5]
    #     ]

    #     grouped = group_task_by_scheduled_task([
    #         task1,
    #         task2,
    #         task3,
    #         task4,
    #         task5,
    #     ])

    #     self.assertListEqual(expected_group, grouped)