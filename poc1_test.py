import unittest
from .poc1 import Task, get_group_task_date

class TestAssignmentPOC1(unittest.TestCase):
    def test_get_group_task_date(self):
        tasks = [
            Task(0, 1, '2018-03-03', 0),
            Task(0, 2, '2018-03-03', 1),
            Task(0, 3, '2018-03-03', 2),
            Task(1, 1, '2018-03-02', 3),
            Task(2, 1, '2018-03-04', 4),
            Task(3, 1, '2018-03-03', 5),
            Task(3, 1, '2018-03-04', 6),
        ]
        expected_grouped = [
            [0, 1, 2, 5],
            [3],
            [4, 6]
        ]

        # Act
        grouped = get_group_task_date(tasks)

        # Assert
        self.assertListEqual(grouped, expected_grouped)
