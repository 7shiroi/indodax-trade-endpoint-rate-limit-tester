import hmac
import time
import hashlib
import asyncio
import aiohttp
from urllib.parse import urlencode
from datetime import datetime

class IndodaxSinglePairTester:
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key.encode()
        self.base_url = "https://indodax.com/tapi"

    def _generate_signature(self, params):
        encoded_params = urlencode(params)
        signature = hmac.new(self.secret_key, encoded_params.encode(), hashlib.sha512)
        return signature.hexdigest()

    async def send_trade_request(self, session, pair, request_id):
        base_currency = pair.split('_')[0]
        params = {
            'method': 'trade',
            'timestamp': int(time.time() * 1000),
            'recvWindow': 5000,
            'pair': pair,
            'type': 'buy',
            'price': '100000',
            'order_type': 'limit'
        }
        
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

    async def run_test(self, pair, num_requests, initial_delay=0.060):
        async with aiohttp.ClientSession() as session:
            results = []
            backoff = initial_delay
            consecutive_errors = 0

            print(f"Starting single pair test for {pair} at {datetime.now()}")
            print(f"Initial delay: {initial_delay}s")
            print("-" * 50)

            for i in range(num_requests):
                result = await self.send_trade_request(session, pair, i)
                results.append(result)

                # Print real-time feedback
                print(f"Request {i} at {result['timestamp']}: Status {result['status']}")
                if isinstance(result['response'], dict):
                    error = result['response'].get('error_code')
                    if error:
                        print(f"Error: {error}")
                        consecutive_errors += 1
                        # Increase backoff if we hit rate limits
                        if error == 'too_many_requests_from_your_ip':
                            backoff = min(backoff * 2, 5.0)  # Double backoff up to 5 seconds
                            print(f"Rate limit hit. Increasing delay to {backoff}s")
                    else:
                        consecutive_errors = 0
                        # Gradually reduce backoff if successful
                        backoff = max(initial_delay, backoff / 1.5)
                
                if i < num_requests - 1:  # Don't sleep after the last request
                    print(f"Sleeping for {backoff}s...")
                    print("-" * 30)
                    await asyncio.sleep(backoff)

            return results

async def main():
    # Replace with your API credentials
    api_key = "YOUR_API_KEY"
    secret_key = "YOUR_SECRET_KEY"

    # Test parameters
    pair = 'btc_idr'  # or 'eth_idr'
    num_requests = 120  # Number of requests to send
    initial_delay = 0.060  # 60ms initial delay

    tester = IndodaxSinglePairTester(api_key, secret_key)
    results = await tester.run_test(pair, num_requests, initial_delay)

    # Final analysis
    print("\nTest Summary:")
    print("-" * 50)
    success = len([r for r in results if isinstance(r['status'], int) and r['status'] == 200])
    errors = len(results) - success
    
    print(f"Total requests: {len(results)}")
    print(f"Successful requests: {success}")
    print(f"Failed requests: {errors}")
    
    # Calculate average time between requests
    timestamps = [datetime.strptime(r['timestamp'], '%Y-%m-%d %H:%M:%S.%f') for r in results]
    if len(timestamps) > 1:
        intervals = [(timestamps[i+1] - timestamps[i]).total_seconds() for i in range(len(timestamps)-1)]
        avg_interval = sum(intervals) / len(intervals)
        print(f"\nAverage interval between requests: {avg_interval:.3f}s")

    # Show error distribution
    error_types = {}
    for r in results:
        if isinstance(r['response'], dict) and 'error_code' in r['response']:
            error_code = r['response']['error_code']
            error_types[error_code] = error_types.get(error_code, 0) + 1
    
    if error_types:
        print("\nError distribution:")
        for error_code, count in error_types.items():
            print(f"{error_code}: {count} times")

if __name__ == "__main__":
    asyncio.run(main()) 