# Runtastic to Strava

Migrate your [Runtastic](https://www.runtastic.com/) activites to [Strava](https://www.strava.com).

We assume that you have a Runtastic account with the desired activities and that you've already signed up for Strava. Our tool migrates the following properties: date, duration, type of activity and distance.
The description consists of the following if available:
```
Feeling: sluggish, average pace: 0.4093538258575198 ?(min/km), max. speed: 3.878333333333333 ?(min/km), elevation gain: 145 m, elevation loss: 151 m, pause: 0.0183 minutes, calories: 182
```

"My Activities" page after import:
![The final result of the data import](docs%2Fdata_import_result.png)

## Export of data

To start you'll need to export your personal data from the runtastic, which can be done under *Settings > Account & Data*. Please note that this may take a few days.

Once your data is available, you should receive an email that contains a link to a `zip` archive, which you have to download. Once you extract this archive you should see a couple of folders inside the extracted archive, the important one being `./Sport-sessions`, which contains one `json` file per activity that you have completed (or added manually) in Runtastic. Once you have access to those `json` files you are able to continue with the actual process of migrating the activities to Strava.

## Strava API Authorization

To start, you'll need to create a Strava API Application through the [Strava settings](https://www.strava.com/settings/api). The website field during the creation of the application can be arbitrary, the *Authorization Callback Domain* should point to your `localhost`, we have chosen `localhost:8080` since nothing is running on this port on our machines. Once this is done, you have to request an authorization code with write permissions (since you want to create new activites through the API), which can be done by copying the link address of your *OAuth Authorization page*, a link to this page is on the bottom part of the [API settings page](https://developers.strava.com/docs/authentication/) and appending the query parameter `&scope=activity:write`, resulting in a URL that should look something like this:

```
https://www.strava.com/oauth/authorize?client_id=[CLIENT_ID]&response_type=code&redirect_uri=http://localhost:8080&approval_prompt=force&scope=activity:write
```

After visiting this URL and clicking the "Authorize" button, you should be redirected to your *Authorization Callback Domain*, in our case `localhost:8080`. The URL should contain a `code` parameter and a parameter scope, which should be `scope=read,activity:write`.

> **_INFO:_** The response looks a bit weird because it tries to redirect to http://localhost:8080/?state=&code=CODE&scope=read,activity:write, which is not possible, but you still get the `code` to extract.

The code is required to obtain a temporary access token, which can be done as follows (we are using [httpie](https://httpie.org/)):

```
$ http POST https://www.strava.com/api/v3/oauth/token client_id=[CLIENT_ID] client_secret=[CLIENT_SECRET] code=[CODE] grant_type=authorization_code
```

[curl}(https://curl.se/):
```
curl -X POST https://www.strava.com/api/v3/oauth/token -d client_id=[CLIENT_ID] -d client_secret=[CLIENT_SECRET] -d code=[CODE] -d grant_type=authorization_code
```

The returned `json` response contains an access token (property `access_token`), its expiration information and the athlete's data. This access token can now be used to make calls to the Strava API. The access token expires [six hours](https://developers.strava.com/docs/authentication/#:~:text=six%20hours) after its creation, so make sure you start your migration within that timespan. Otherwise, you have to redo the above steps to get a new access token. 

## Migration of data

While it is possible to use our tool with "plain" python, we strongly recommend using [Docker](https://www.docker.com/). In both cases you have to clone this repository using `git clone https://github.com/matthiasweiss/runtastic-strava-migrate` and subsequently copy the aforementioned `./Sport-sessions` folder, which is part of the personal data you are able to export from Runtastic, into the repository's root. After copying the files into the cloned repository, listing all files within the directory using `ls` should yield something like this:

```
$ ls -1F

Dockerfile
LICENSE
README.md
Sport-sessions/
docker_migrate.sh*
migrate.py
requirements.txt
```

### Using Docker (recommended):

We've prepared a script that builds the necessary image, migrates your data and removes the image after the script is done migrating. It is sufficient to run the following two commands (`ACCESS_TOKEN` is the access token that was obtained earlier):

```
$ chmod +x docker_migrate.sh

$ ./docker_migrate.sh ACCESS_TOKEN
```

### Using Python 3.7+:

Make sure that your Python version is 3.7 or higher by checking your via the `python3 --version` command. Once that is done install all necessary dependencies using the `pip3 install -r ./requirements.txt` command. Now you should be able to run `python3 migrate.py ACCESS_TOKEN`, where `ACCESS_TOKEN` once again is the access token for the Strava API.

We do not recommend this approach since Python is quite known for its frustrating dependency management (see [here](https://medium.com/knerd/the-nine-circles-of-python-dependency-hell-481d53e3e025) for example).

---

It is furthermore noteworthy that the Strava API is limited to 100 requests every 15 minutes and 1000 requests per day, thus it could become a problem if you want to import a lot of activities at once.