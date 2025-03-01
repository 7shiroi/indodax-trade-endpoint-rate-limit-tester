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
        self.base_url = "https://btcapi.net/tapi"
        # self.base_url = "https://indodax.com/tapi"

    def _generate_signature(self, params):
        encoded_params = urlencode(params)
        signature = hmac.new(self.secret_key, encoded_params.encode(), hashlib.sha512)
        return signature.hexdigest()

    async def send_trade_request(self, session, pair, request_id):
        # Prepare parameters for a minimal trade request
        base_currency = pair.split('_')[0]  # Extract base currency (btc or eth)
        params = {
            'method': 'trade',
            'timestamp': int(time.time() * 1000),
            'recvWindow': 1000,
            'pair': pair,
            'type': 'buy',
            'price': '50000000000',  # Lower price
            'order_type': 'limit'
        }
        
        # Set the correct currency amount parameter
        if base_currency == 'btc':
            params['btc'] = '0.00001'
        elif base_currency == 'eth':
            params['eth'] = '0.00001'

        signature = self._generate_signature(params)
        headers = {
            'Key': self.api_key,
            'Sign': signature
        }

        request_timestamp = datetime.now()
        start_time = time.time()
        try:
            async with session.post(self.base_url, headers=headers, data=params) as response:
                result = await response.json()
                end_time = time.time()
                return {
                    'request_id': request_id,
                    'pair': pair,
                    'status': response.status,
                    'response': result,
                    'time': end_time - start_time,
                    'timestamp': request_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')
                }
        except Exception as e:
            end_time = time.time()
            return {
                'request_id': request_id,
                'pair': pair,
                'status': 'error',
                'response': str(e),
                'time': end_time - start_time,
                'timestamp': request_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')
            }

    async def run_pair_requests(self, session, pair, requests_per_pair, start_id):
        results = []
        for i in range(requests_per_pair):
            request_id = start_id + i
            # Execute each request immediately and wait for it
            result = await self.send_trade_request(session, pair, request_id)
            results.append(result)
            if i < requests_per_pair - 1:  # Don't sleep after the last request
                await asyncio.sleep(0.060)  # 60ms interval
        return results

    async def run_rate_limit_test(self, pairs, requests_per_pair):
        async with aiohttp.ClientSession() as session:
            # Create tasks for each pair - pairs will run concurrently
            tasks = [
                self.run_pair_requests(session, pair, requests_per_pair, i * requests_per_pair)
                for i, pair in enumerate(pairs)
            ]
            
            # Execute all pairs concurrently
            all_results = await asyncio.gather(*tasks)
            # Flatten results
            return [item for sublist in all_results for item in sublist]

async def main():
    # Replace with your API credentials
    api_key = "YOUR_API_KEY"
    secret_key = "YOUR_SECRET_KEY"

    # Test parameters
    pairs = ['btc_idr', 'eth_idr']  # Test multiple pairs
    requests_per_pair = 60  # Number of requests per pair

    tester = IndodaxRateLimitTester(api_key, secret_key)
    
    print(f"Starting rate limit test at {datetime.now()}")
    print(f"Testing {len(pairs)} pairs with {requests_per_pair} requests each")
    print("Pairs:", pairs)
    print("-" * 50)

    results = await tester.run_rate_limit_test(pairs, requests_per_pair)

    # Analyze results
    for pair in pairs:
        pair_results = [r for r in results if r['pair'] == pair]
        success = len([r for r in pair_results if isinstance(r['status'], int) and r['status'] == 200])
        errors = len(pair_results) - success
        
        print(f"\nResults for {pair}:")
        print(f"Successful requests: {success}")
        print(f"Failed requests: {errors}")
        
        # Sort results by request_id for chronological order
        pair_results.sort(key=lambda x: x['request_id'])
        
        success_responses = [r for r in pair_results if isinstance(r['status'], int) and r['status'] == 200]
        if success_responses:
            print("\nSuccess responses:")
            for s in success_responses:
                print(f"Request {s['request_id']} at {s['timestamp']}: {s['response']}")
        
        error_responses = [r for r in pair_results if isinstance(r['status'], int) and r['status'] != 200]
        if error_responses:
            print("\nError responses:")
            for err in error_responses:
                print(f"Request {err['request_id']} at {err['timestamp']}: {err['response']}")

if __name__ == "__main__":
    asyncio.run(main())