import hmac
import time
import hashlib
import asyncio
import aiohttp
from urllib.parse import urlencode
from datetime import datetime
import sys

# Add this at the beginning of your script, before any other asyncio operations
if sys.platform.startswith('win'):
    # Force use of selector event loop on Windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class IndodaxRateLimitTester:
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key.encode()
        # Use the official endpoint
        # self.base_url = "https://indodax.com/tapi"
        self.base_url = "https://btcapi.net/tapi"

    def _generate_signature(self, params):
        encoded_params = urlencode(params)
        signature = hmac.new(self.secret_key, encoded_params.encode(), hashlib.sha512)
        return signature.hexdigest()

    async def send_trade_request(self, session, pair, request_id):
        request_start = datetime.now()  # Changed to datetime for consistent format
        
        params = {
            'method': 'trade',
            'timestamp': int(time.time() * 1000),
            'recvWindow': 5000,  # Using default recvWindow
            'pair': pair,
            'type': 'buy',
            'price': '50000000000',
            'order_type': 'limit'
        }
        
        base_currency = pair.split('_')[0]
        params[base_currency] = '0.00001'

        signature = self._generate_signature(params)
        headers = {
            'Key': self.api_key,
            'Sign': signature
        }

        try:
            async with session.post(self.base_url, headers=headers, data=params) as response:
                result = await response.json()
                request_end = datetime.now()
                
                # Check for the specific rate limit error message
                is_rate_limited = False
                error_msg = result.get('error', '')
                if error_msg and 'try again in 5 seconds' in error_msg.lower():
                    is_rate_limited = True
                
                return {
                    'request_id': request_id,
                    'pair': pair,
                    'status': response.status,
                    'response': result,
                    'time': (time.time() * 1000 - request_start.timestamp() * 1000) / 1000,
                    'requested_at': request_start.strftime('%Y-%m-%d %H:%M:%S.%f'),
                    'finished_at': request_end.strftime('%Y-%m-%d %H:%M:%S.%f'),
                    'is_rate_limited': is_rate_limited
                }
        except Exception as e:
            request_end = datetime.now()
            return {
                'request_id': request_id,
                'pair': pair,
                'status': 'error',
                'response': str(e),
                'time': (time.time() * 1000 - request_start.timestamp() * 1000) / 1000,
                'requested_at': request_start.strftime('%Y-%m-%d %H:%M:%S.%f'),
                'finished_at': request_end.strftime('%Y-%m-%d %H:%M:%S.%f'),
                'is_rate_limited': False
            }

    async def run_pair_requests(self, session, pair, requests_per_pair, start_id):
        results = []
        tasks = []
        print(f"\nTesting rate limit for pair {pair}")
        print(f"{'Request ID':^10} | {'Pair':^8} | {'Status':^8} | {'Time (s)':^10} | {'Rate Limited':^12} | "
              f"{'Requested At':^26} | {'Finished At':^26}")
        print("-" * 120)
        
        # Create all tasks first with 60ms intervals
        for i in range(requests_per_pair):
            request_id = start_id + i
            task = asyncio.create_task(
                self.send_trade_request(session, pair, request_id)
            )
            tasks.append(task)
            await asyncio.sleep(0.060)  # Wait 60ms before scheduling next request
        
        # Wait for all results
        results = await asyncio.gather(*tasks)
        
        # Print results as they come in
        for result in results:
            status = result['status'] if isinstance(result['status'], int) else 'ERROR'
            print(f"{result['request_id']:^10} | {result['pair']:^8} | {status:^8} | "
                  f"{result['time']:^10.3f} | {result['is_rate_limited']:^12} | "
                  f"{result['requested_at']} | {result['finished_at']}")
            
        return results

    async def run_rate_limit_test(self, pairs, requests_per_pair):
        print("\nRate Limit Test Configuration:")
        print(f"- Testing trade endpoint rate limit (20 requests/second/pair)")
        print(f"- Pairs to test: {', '.join(pairs)}")
        print(f"- Requests per pair: {requests_per_pair}")
        print(f"- Request interval: 60ms (~16.67 requests/second)")
        
        async with aiohttp.ClientSession() as session:
            all_results = []
            for i, pair in enumerate(pairs):
                results = await self.run_pair_requests(session, pair, requests_per_pair, i * requests_per_pair)
                all_results.extend(results)
            return all_results

async def main():
    api_key = "YOUR_API_KEY"
    secret_key = "YOUR_SECRET_KEY"

    # Test parameters
    pairs = ['btc_idr']  # Test one pair at a time
    requests_per_pair = 300  # Enough requests to see rate limit behavior

    tester = IndodaxRateLimitTester(api_key, secret_key)
    
    print(f"\n{'=' * 50}")
    print(f"Starting rate limit test at {datetime.now()}")
    print(f"{'=' * 50}")

    results = await tester.run_rate_limit_test(pairs, requests_per_pair)

    # Analyze results
    print(f"\n{'=' * 50}")
    print("Test Summary")
    print(f"{'=' * 50}")
    
    for pair in pairs:
        pair_results = [r for r in results if r['pair'] == pair]
        success = len([r for r in pair_results if isinstance(r['status'], int) and r['status'] == 200])
        errors = len(pair_results) - success
        
        print(f"\nResults for {pair}:")
        print(f"{'=' * 20}")
        print(f"Successful requests: {success}")
        print(f"Failed requests: {errors}")
        
        # Sort results by request_id for chronological order
        pair_results.sort(key=lambda x: x['request_id'])
        
        error_responses = [r for r in pair_results if isinstance(r['status'], int) and r['status'] != 200]
        if error_responses:
            print("\nError responses:")
            print("-" * 20)
            for err in error_responses:
                print(f"Request {err['request_id']} at {err['finished_at']}: {err['response']}")

if __name__ == "__main__":
    asyncio.run(main())