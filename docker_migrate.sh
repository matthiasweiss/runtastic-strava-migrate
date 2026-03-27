
# Check arguments
if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    echo "Usage: $0 ACCESS_TOKEN [MAX_UPLOADS]"
    echo "  ACCESS_TOKEN: Your Strava API access token"
    echo "  MAX_UPLOADS: Optional - maximum number of activities to upload (default: all)"
    exit 1
fi

echo "Building image dsue/runtastic-strava-migrate"
echo "--------------------------------------------"
docker build -t dsue/runtastic-strava-migrate --load .
echo ""

echo "Migrating activities"
echo "--------------------------------------------"

# Pass both arguments if MAX_UPLOADS is provided
if [ $# -eq 2 ]; then
    docker run --rm dsue/runtastic-strava-migrate $1 $2
else
    docker run --rm dsue/runtastic-strava-migrate $1
fi
echo ""

echo "Removing image dsue/runtastic-strava-migrate"
echo "--------------------------------------------"
docker image rmi dsue/runtastic-strava-migrate
echo ""
