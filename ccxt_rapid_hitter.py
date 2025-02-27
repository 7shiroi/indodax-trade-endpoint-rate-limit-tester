import ccxt
import time
import asyncio
from datetime import datetime
import aiohttp

class IndodaxRateLimitTester:
    def __init__(self, api_key, secret_key):
        self.exchange = ccxt.indodax({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': False  # We'll handle rate limiting manually
        })
        
    async def send_trade_request(self, pair, request_id):
        # Prepare minimal trade parameters
        request_timestamp = datetime.now()
        start_time = time.time()
        
        try:
            # Create a minimal limit order
            params = {
                'type': 'limit',
                'client_order_id': f'test_{request_id}'  # Added client_order_id support
            }
            
            result = await self.exchange.create_order(
                symbol=pair,
                type='limit',
                side='buy',
                amount=0.00001,  # Minimal amount
                price=50000000000,  # Very low price to avoid execution
                params=params
            )
            
            end_time = time.time()
            return {
                'request_id': request_id,
                'pair': pair,
                'status': 200,  # Successful API call
                'response': result,
                'time': end_time - start_time,
                'timestamp': request_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')
            }
            
        except ccxt.NetworkError as e:
            end_time = time.time()
            return {
                'request_id': request_id,
                'pair': pair,
                'status': 'network_error',
                'response': str(e),
                'time': end_time - start_time,
                'timestamp': request_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')
            }
        except ccxt.ExchangeError as e:
            end_time = time.time()
            return {
                'request_id': request_id,
                'pair': pair,
                'status': 'exchange_error',
                'response': str(e),
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

    async def run_pair_requests(self, pair, requests_per_pair, start_id):
        results = []
        for i in range(requests_per_pair):
            request_id = start_id + i
            result = await self.send_trade_request(pair, request_id)
            results.append(result)
            if i < requests_per_pair - 1:  # Don't sleep after the last request
                await asyncio.sleep(0.060)  # 60ms interval
        return results

    async def run_rate_limit_test(self, pairs, requests_per_pair):
        tasks = [
            self.run_pair_requests(pair, requests_per_pair, i * requests_per_pair)
            for i, pair in enumerate(pairs)
        ]
        
        all_results = await asyncio.gather(*tasks)
        return [item for sublist in all_results for item in sublist]

async def main():
    # Replace with your API credentials
    api_key = "YOUR_API_KEY"
    secret_key = "YOUR_SECRET_KEY"

    # Test parameters
    pairs = ['BTC/IDR', 'ETH/IDR']  # CCXT uses standard market symbols
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
        success = len([r for r in pair_results if r['status'] == 200])
        errors = len(pair_results) - success
        
        print(f"\nResults for {pair}:")
        print(f"Successful requests: {success}")
        print(f"Failed requests: {errors}")
        
        # Sort results by request_id for chronological order
        pair_results.sort(key=lambda x: x['request_id'])
        
        # Print successful responses
        success_responses = [r for r in pair_results if r['status'] == 200]
        if success_responses:
            print("\nSuccess responses:")
            for s in success_responses:
                print(f"Request {s['request_id']} at {s['timestamp']}: {s['response']}")
        
        # Print error responses
        error_responses = [r for r in pair_results if r['status'] != 200]
        if error_responses:
            print("\nError responses:")
            for err in error_responses:
                print(f"Request {err['request_id']} at {err['timestamp']}: {err['response']}")

if __name__ == "__main__":
    asyncio.run(main())