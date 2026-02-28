#!/bin/bash
# Verify no overbooking after stress test

echo "========================================"
echo "OVERBOOKING VERIFICATION"
echo "========================================"
echo ""

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found"
    exit 1
fi

# Run SQL query
docker compose -f backend/docker/docker-compose.yml exec -T db psql -U postgres -d event_booking << 'EOF'

-- Check for overbooking
SELECT 
    e.id,
    e.title,
    e.seat_count,
    e.available_seats,
    COUNT(b.id) as total_bookings,
    SUM(b.seat_count) as seats_booked,
    CASE 
        WHEN SUM(b.seat_count) > e.seat_count THEN '❌ OVERBOOKED'
        WHEN e.available_seats < 0 THEN '❌ NEGATIVE SEATS'
        ELSE '✓ OK'
    END as status
FROM events e
LEFT JOIN bookings b ON e.id = b.event_id AND b.status = 'confirmed'
GROUP BY e.id, e.title, e.seat_count, e.available_seats
HAVING COUNT(b.id) > 0
ORDER BY e.id DESC
LIMIT 20;

EOF

echo ""
echo "If any row shows OVERBOOKED or NEGATIVE SEATS → FAILED"
echo ""
