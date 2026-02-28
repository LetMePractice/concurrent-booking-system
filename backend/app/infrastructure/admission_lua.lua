-- Atomic admission control script
-- Checks available seats and reserves if possible
--
-- KEYS[1]: seats:{event_id} - available seats counter
-- KEYS[2]: reserved:{event_id} - reserved seats counter
-- ARGV[1]: seats to reserve
--
-- Returns:
--   1 if admitted (reservation successful)
--   0 if rejected (sold out)

local available = tonumber(redis.call('GET', KEYS[1]) or 0)
local reserved = tonumber(redis.call('GET', KEYS[2]) or 0)
local requested = tonumber(ARGV[1])

-- Check if enough capacity
if available - reserved < requested then
    return 0  -- Reject
end

-- Reserve seats
redis.call('INCRBY', KEYS[2], requested)
redis.call('EXPIRE', KEYS[2], 30)  -- 30s TTL for reservation

return 1  -- Admitted
