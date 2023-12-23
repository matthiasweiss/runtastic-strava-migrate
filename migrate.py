import glob
import json
import sys
import requests
import datetime

# check if correct arguments are passed to the script
if len(sys.argv) != 2:
    print("Usage: {} ACCESS_TOKEN".format(sys.argv[0]))
    sys.exit(0)

# directory which contains the activity JSON files
DATA_DIR = "./Sport-sessions"

# store access token for Strava API
ACCESS_TOKEN = sys.argv[1]

# Strava API endpoint
STRAVA_ENDPOINT = "https://www.strava.com/api/v3/activities"

activities = []

# store each activity (one per JSON file) in the activities list
for path in glob.glob(DATA_DIR + "/*.json"):
    with open(path, "r") as json_file:
        activities.append(json.load(json_file))


# No official documentation, took activity types from
# https://github.com/Metalnem/runtastic/blob/master/api/api.go
# and mapped it to the corresponding Strava activity types at
# https://developers.strava.com/docs/reference/#api-models-ActivityType
def strava_activity_type(runtastic_type_id):
    walk = "Walk"
    run = "Run"
    swim = "Swim"
    ride = "Ride"

    return {
        2: walk, 7: walk, 19: walk,
        3: ride, 4: ride, 15: ride, 22: ride,
        18: swim
    }.get(int(runtastic_type_id), run)


# map runtastic data to strava API request and make API call
def import_activity(counter, activity):
    activity_type = strava_activity_type(activity['sport_type_id'])
    activity_date = datetime.datetime.fromtimestamp(int(activity['start_time']) / 1000).isoformat()

    print("[#{}] Importing {} from {}".format(counter, activity_type, activity_date))

    data = {}
    for feature in activity["features"]:
        if feature['type'] == "track_metrics":
            feeling = activity["subjective_feeling"] if (
                    "subjective_feeling" in activity) else "unknown"
            data = {
                "name": "{} ({})".format(activity_type, activity_date),
                "type": activity_type,
                "start_date_local": activity_date + "Z",
                "elapsed_time": int(int(activity["duration"]) / 1000),
                "distance": int(feature["attributes"]["distance"]),
                "description": "Feeling: " + feeling + ""
                                                                   ", average pace: " + str(
                    feature["attributes"]["average_pace"]) + " ?(min/km)" # The unit of measurement is not clear
                                                             ", max. speed: " + str(
                    feature["attributes"]["max_speed"]) + " ?(min/km)" # The unit of measurement is not clear
                                                          ", elevation gain: " + str(
                    feature["attributes"]["elevation_gain"]) + " m"
                                                               ", elevation loss: " + str(
                    feature["attributes"]["elevation_loss"]) + " m"
                                                               ", pause: " + str(
                    int(activity["pause"]) / 1000 / 60) + " minutes"
                                                          ", calories: " + str(activity["calories"])
            }
            # INFO: For debugging purposes
            # print("[#{}] Request data: {}".format(count, data))
        else:
            continue

    headers = {
        "Authorization": "Bearer {}".format(ACCESS_TOKEN)
    }

    response = requests.post(STRAVA_ENDPOINT, data=data, headers=headers)

    if response.status_code == requests.codes.created:
        print("[#{}] Import successful!".format(counter))
    # the Strava API returns a strange error if an activity already exists, since
    # this could happen quite easily we decided to handle this error explicitly
    elif response.status_code == 409:
        print("[#{}] Import failed, activity already exists!".format(counter))
    else:
        print("[#{}] Import failed, response was: \n{}\n".format(counter, response.text))



# import all activities into Strava
counter_activities = 1
for activity in activities:
    import_activity(counter_activities, activity)
    counter_activities += 1
