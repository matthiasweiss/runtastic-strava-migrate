echo "Building image dsue/runtastic-strava-migrate"
echo "--------------------------------------------"
docker build -t dsue/runtastic-strava-migrate --load .
echo ""

echo "Migrating activities"
echo "--------------------------------------------"

docker run --rm dsue/runtastic-strava-migrate $1
echo ""

echo "Removing image dsue/runtastic-strava-migrate"
echo "--------------------------------------------"
docker image rmi dsue/runtastic-strava-migrate
echo ""
