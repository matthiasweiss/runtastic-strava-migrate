import glob
import json
import sys
import requests
import datetime
import os
import time

# check if correct arguments are passed to the script
if len(sys.argv) < 2 or len(sys.argv) > 3:
    print("Usage: {} ACCESS_TOKEN [MAX_UPLOADS]".format(sys.argv[0]))
    print("  ACCESS_TOKEN: Your Strava API access token")
    print("  MAX_UPLOADS: Optional - maximum number of activities to upload (default: all)")
    sys.exit(0)

# directory which contains the activity JSON files
DATA_DIR = "./Sport-sessions"
GPS_DATA_DIR = "./Sport-sessions/GPS-data"

# store access token for Strava API
ACCESS_TOKEN = sys.argv[1]

# optional max uploads limit
MAX_UPLOADS = int(sys.argv[2]) if len(sys.argv) == 3 else None

# Strava API endpoints
STRAVA_ENDPOINT = "https://www.strava.com/api/v3/activities"
STRAVA_UPLOAD_ENDPOINT = "https://www.strava.com/api/v3/uploads"

activities = []
gpx_activities = []

# store each activity (one per JSON file) in both lists
for path in glob.glob(DATA_DIR + "/*.json"):
    with open(path, "r") as json_file:
        activity_data = json.load(json_file)
        activities.append(activity_data)

        # Add GPX path since we've ensured all JSON files have corresponding GPX files
        json_filename = os.path.basename(path)
        gpx_filename = json_filename.replace('.json', '.gpx')
        gpx_path = os.path.join(GPS_DATA_DIR, gpx_filename)
        activity_data_gpx = activity_data.copy()
        activity_data_gpx['gpx_path'] = gpx_path
        gpx_activities.append(activity_data_gpx)


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


def metersPerSecondToKmPerHour(metersPerSecond: float):
    # km/h to m/s
    # 1m/s = (1km/1000) / (1h/(60*60))
    # m/s * 3.6 = km/h
    kilometersPerHour = float(metersPerSecond)*3.6
    return f'{kilometersPerHour:2.2f}'

def convertToMinPerKm(secondsPerMeter: float):
    secondsPerKilometer = float(secondsPerMeter) * 1000.0
    return convertSecondsToFormattedString(secondsPerKilometer)

def convertToSecondsString(milliseconds: int):
    seconds = round(milliseconds/1000.0)
    return convertSecondsToFormattedString(seconds)

def convertSecondsToFormattedString(second: int):
    s = int(second)
    min = int(s/60)
    seconds = s - min*60
    result = f'{min:02d}:{seconds:02d}'
    return result


# Upload GPX file to Strava using upload endpoint
def upload_gpx_activity(counter, activity):
    activity_type = strava_activity_type(activity['sport_type_id'])
    activity_date = datetime.datetime.fromtimestamp(int(activity['start_time']) / 1000).isoformat()

    print("[#{}] Uploading {} from {} with GPX track".format(counter, activity_type, activity_date))

    # Prepare description from activity data
    feeling = activity.get("subjective_feeling", "unknown")
    pauseInMs = int(activity["pause"])
    pauseString = (", pause: " + convertToSecondsString(pauseInMs) + " min") if (int(pauseInMs / 1000) > 0) else ""

    description = "Feeling: " + feeling + pauseString + ", calories: " + str(activity["calories"])

    headers = {
        "Authorization": "Bearer {}".format(ACCESS_TOKEN)
    }

    files = {
        'file': open(activity['gpx_path'], 'rb')
    }

    data = {
        'name': "{} ({})".format(activity_type, activity_date),
        'description': description,
        'data_type': 'gpx'
    }

    try:
        response = requests.post(STRAVA_UPLOAD_ENDPOINT, files=files, data=data, headers=headers)

        if response.status_code == 201:
            upload_data = response.json()
            print("[#{}] GPX upload successful! Upload ID: {}".format(counter, upload_data.get('id')))
            return True
        elif response.status_code == 409:
            print("[#{}] Upload failed, activity already exists!".format(counter))
            return False
        else:
            print("[#{}] Upload failed, response was: \n{}\n".format(counter, response.text))
            return False
    except Exception as e:
        print("[#{}] Upload failed with exception: {}".format(counter, str(e)))
        return False
    finally:
        files['file'].close()

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
            pauseInMs = int(activity["pause"])
            pauseString = (", pause: " + convertToSecondsString(pauseInMs) + " min") if (int(pauseInMs / 1000) > 0) else ""
            
            data = {
                "name": "{} ({})".format(activity_type, activity_date),
                "type": activity_type,
                "start_date_local": activity_date + "Z",
                "elapsed_time": int(int(activity["duration"]) / 1000),
                "distance": int(feature["attributes"]["distance"]),
                "description": "Feeling: " + feeling
                + ", average pace: " + convertToMinPerKm(feature["attributes"]["average_pace"]) + " min/km"
                + ", average speed: " + metersPerSecondToKmPerHour(feature["attributes"]["average_speed"]) + " km/h"
                + ", max. speed: " + metersPerSecondToKmPerHour(feature["attributes"]["max_speed"]) + " km/h"
                + ", elevation gain: " + str(feature["attributes"]["elevation_gain"]) + " m"
                + ", elevation loss: " + str(feature["attributes"]["elevation_loss"]) + " m"
                + pauseString
                + ", calories: " + str(activity["calories"])
            }
            # INFO: For debugging purposes
            # print("[#{}] Request data: {}".format(counter, data))
        else:
            continue

    headers = {
        "Authorization": "Bearer {}".format(ACCESS_TOKEN)
    }

    response = requests.post(STRAVA_ENDPOINT, data=data, headers=headers)

    if response.status_code == requests.codes.created:
        print("[#{}] JSON Import successful!".format(counter))
        return True
    # the Strava API returns a strange error if an activity already exists, since
    # this could happen quite easily we decided to handle this error explicitly
    elif response.status_code == 409:
        print("[#{}] JSON Import failed, activity already exists!".format(counter))
        return False
    else:
        print("[#{}] JSON Import failed, response was: \n{}\n".format(counter, response.text))
        return False



# Choose which upload method to use
total_activities = len(gpx_activities)
max_uploads_text = "all {} activities".format(total_activities) if MAX_UPLOADS is None else "{} activities".format(min(MAX_UPLOADS, total_activities))
print("Found {} activities for JSON-only upload and {} activities for GPX upload".format(len(activities), total_activities))
print("Will upload {} using GPX method...".format(max_uploads_text))

# import GPX activities into Strava (up to MAX_UPLOADS limit)
counter_activities = 1
successful_uploads = []
failed_uploads = []

activities_to_process = gpx_activities[:MAX_UPLOADS] if MAX_UPLOADS else gpx_activities

for activity in activities_to_process:
    success = upload_gpx_activity(counter_activities, activity)

    if success:
        successful_uploads.append(activity)
    else:
        failed_uploads.append(activity)

    counter_activities += 1
    time.sleep(1)  # Rate limiting to respect Strava API limits

print("\nUpload completed: {} successful, {} failed".format(len(successful_uploads), len(failed_uploads)))

# Delete successfully uploaded files
if successful_uploads:
    print("\nDeleting successfully uploaded files...")
    for activity in successful_uploads:
        try:
            # Delete JSON file
            json_path = None
            for path in glob.glob(DATA_DIR + "/*.json"):
                with open(path, "r") as f:
                    data = json.load(f)
                    if data.get('id') == activity.get('id'):
                        json_path = path
                        break

            if json_path:
                os.remove(json_path)
                print("Deleted: {}".format(os.path.basename(json_path)))

            # Delete GPX file
            if 'gpx_path' in activity and os.path.exists(activity['gpx_path']):
                os.remove(activity['gpx_path'])
                print("Deleted: {}".format(os.path.basename(activity['gpx_path'])))

        except Exception as e:
            print("Failed to delete files for activity {}: {}".format(activity.get('id'), str(e)))

print("\nRemaining files: {} JSON, {} GPX".format(
    len(glob.glob(DATA_DIR + "/*.json")),
    len(glob.glob(GPS_DATA_DIR + "/*.gpx"))
))

# Uncomment below to test JSON-only uploads for comparison:
# counter_activities = 1
# for activity in activities:
#     import_activity(counter_activities, activity)
#     counter_activities += 1
#     time.sleep(1)
