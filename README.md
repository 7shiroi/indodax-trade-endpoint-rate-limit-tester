# Indodax Trade Endpoint Rate Limit Tester

This tool is designed to test the rate limits of Indodax's trade endpoint as documented in their [official API documentation](https://github.com/btcid/indodax-official-api-docs/blob/master/Private-RestAPI.md#trade-endpoints).

## Background

According to the official documentation, the trade endpoint should have rate limits applied per user and trading pair. However, our testing has revealed an unexpected IP-based rate limiting mechanism that isn't mentioned in the documentation.

## Current Issue

When running concurrent tests across multiple trading pairs (btc_idr and eth_idr), we're encountering:

- Error: `too_many_requests_from_your_ip`
- This suggests an IP-based rate limit rather than the documented user/pair-based limit
- The error occurs after approximately 60 requests per session (if 2 pairs running concurrently, error will occur after approximately 30 requests)

## Setup and Usage

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure your API credentials in the script:

```python
api_key = "YOUR_API_KEY"
secret_key = "YOUR_SECRET_KEY"
```

4. Run the script:

```bash
python rapid_hitter.py
```

## Test Parameters

- Default test runs with 2 pairs (btc_idr and eth_idr)
- Requests per pair: 60
- Interval between requests: 60ms
- Requests are sent concurrently

## Contributing

If you're experiencing similar issues or have found a solution, please:

1. Run the test with your own API credentials
2. Create an issue describing your results
3. Submit a PR if you have a solution

## Note

All test request use minimal amounts and invalid prices to ensure no actual trades occur. However, please review the code and use at your own risk.

## License

MIT
