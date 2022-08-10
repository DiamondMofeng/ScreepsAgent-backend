import asyncio
import unittest
import common.screeps_api_aiohttp as screeps_api_aiohttp


class MyTestCase(unittest.TestCase):
    def test_something(self):
        async def main():
            async with screeps_api_aiohttp.API() as api:
                self.assertEqual(182 * 182, len(await api.get_rooms_of_shard('shard0')))

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())


if __name__ == '__main__':
    unittest.main()
