# Serper Free Tier Optimization

## Problem

Free Serper API keys have limited credits:
- **2,500 credits** (one-time, expire after 6 months)
- **100 requests/second** rate limit
- Each successful API query consumes 1 credit (or 2 if requesting >10 results)

When credits are exhausted, Serper returns **403 Forbidden** errors. The application was treating all 403 errors as invalid keys and failing immediately, without retries.

## Solution

We've implemented several optimizations to better handle free tier quotas:

### 1. Proper Rate Limiting

**Before:** 10 requests/second (below free tier limit but not optimized)

**After:** 90 requests/second (safely under 100/second free tier limit)

```python
# src/tools/rate_limiter.py
def get_serper_limiter(api_key: str | None = None) -> RateLimiter:
    # Free tier: 90/second (safely under 100/second limit)
    return RateLimiterFactory.get("serper", "90/second")
```

This ensures:
- Stays safely under 100 requests/second free tier limit
- Allows high throughput when needed
- Credits are the limiting factor (2,500 total), not rate

### 2. Jitter for Request Spreading

Added random jitter (0-1 second) after acquiring rate limit permission:

```python
# src/tools/rate_limiter.py
async def acquire(self, wait: bool = True, jitter: bool = False) -> bool:
    if self._limiter.hit(self._rate_limit, self._identity):
        if jitter:
            # Add 0-1 second random jitter
            jitter_seconds = random.uniform(0, 1.0)
            await asyncio.sleep(jitter_seconds)
        return True
```

**Benefits:**
- Prevents "thundering herd" - multiple parallel requests hitting at once
- Spreads load slightly to avoid bursts
- Minimal delay (max 1 second)

### 3. Retry Logic for Credit Exhaustion

**Before:** 403 errors → `ConfigurationError` → No retries

**After:** 403 errors → `RateLimitError` → Retry with exponential backoff

```python
# src/tools/vendored/serper_client.py
if response.status == 403:
    # Treat as credit exhaustion (retryable) not invalid key
    raise RateLimitError("Serper API credits may be exhausted...")
```

```python
# src/tools/serper_web_search.py
@retry(
    stop=stop_after_attempt(5),  # 5 retries
    wait=wait_random_exponential(
        multiplier=2, min=5, max=120, exp_base=2
    ),  # 5s to 120s backoff with jitter
)
```

**Retry Schedule:**
- Attempt 1: Immediate
- Attempt 2: Wait 5-10s (with jitter)
- Attempt 3: Wait 10-20s (with jitter)
- Attempt 4: Wait 20-40s (with jitter)
- Attempt 5: Wait 40-80s (with jitter)

### 4. Better Error Messages

The system now distinguishes between:
- **Invalid API key** (ConfigurationError) - No retries, immediate failure
- **Quota exhaustion** (RateLimitError) - Retries with backoff

## Usage

The optimizations are **automatic** - no configuration needed. The system will:

1. **Rate limit** to 1 request per 60 seconds
2. **Add jitter** to spread requests
3. **Retry on 403** with exponential backoff
4. **Log clearly** when quota is exhausted

## Monitoring

Watch for these log messages:

```
Serper API returned 403 Forbidden
May be quota exhaustion (free tier) or invalid key
Retrying with backoff...
```

If you see repeated 403 errors even after retries, your quota is likely exhausted for the day/month.

## Recommendations for Free Tier

1. **Monitor usage** at [serper.dev/dashboard](https://serper.dev/dashboard)
2. **Use DuckDuckGo fallback** when quota exhausted:
   ```bash
   export WEB_SEARCH_PROVIDER=duckduckgo
   ```
3. **Consider paid tier** if you need more requests
4. **Batch requests** - the rate limiter will automatically space them out

## Configuration

To adjust rate limiting (not recommended for free tier):

```python
# In src/tools/rate_limiter.py
# Change from:
return RateLimiterFactory.get("serper", "1/60second")

# To (for paid tier):
return RateLimiterFactory.get("serper", "10/second")
```

## Summary

✅ **Proper rate limiting** (90 req/s, under 100/s limit)  
✅ **Jitter** to spread requests (0-1s)  
✅ **Retry logic** for credit exhaustion  
✅ **Better error handling**  
✅ **Automatic** - no config needed  

**Note:** Free tier provides 2,500 credits (one-time, expire after 6 months). Monitor usage at [serper.dev/dashboard](https://serper.dev/dashboard). Once credits are exhausted, you'll need to upgrade to a paid plan or use DuckDuckGo fallback.

