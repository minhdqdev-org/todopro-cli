#!/usr/bin/env python
"""Test script to debug board view loading."""

import asyncio

from todopro_cli.api.client import get_client
from todopro_cli.api.tasks import TasksAPI


async def main():
    client = get_client("default")
    tasks_api = TasksAPI(client)

    try:
        print("Fetching tasks...")
        tasks_data = await tasks_api.list_tasks()

        if isinstance(tasks_data, dict):
            tasks_list = tasks_data.get("tasks", [])
        else:
            tasks_list = tasks_data

        print(f"Total tasks loaded: {len(tasks_list)}")

        if tasks_list:
            print("\nFirst 5 tasks:")
            for i, task in enumerate(tasks_list[:5]):
                print(f"  {i + 1}. {task['content'][:60]}")
        else:
            print("No tasks found!")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
