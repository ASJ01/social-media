import os
import requests
from flask import Flask, redirect, request, session, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")


@app.route("/")
def home():
    return '<a href="/login">Link your LinkedIn account</a>'


@app.route("/login")
def login():
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=r_liteprofile%20w_member_social"
    )
    return redirect(auth_url)


@app.route("/callback")
def callback():
    code = request.args.get("code")

    # Exchange code for access token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    response = requests.post(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    token_info = response.json()

    access_token = token_info.get("access_token")
    if not access_token:
        return "Failed to get access token", 400

    session["access_token"] = access_token
    return redirect("/post")


@app.route("/post", methods=["GET", "POST"])
def post_to_linkedin():
    access_token = session.get("access_token")
    if not access_token:
        return redirect("/login")

    # Get user URN (ID)
    profile_url = "https://api.linkedin.com/v2/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    profile_response = requests.get(profile_url, headers=headers)
    profile_data = profile_response.json()
    urn = profile_data.get("id")

    if request.method == "POST":
        message = request.form.get("message")

        post_data = {
            "author": f"urn:li:person:{urn}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": message},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }

        post_url = "https://api.linkedin.com/v2/ugcPosts"
        post_response = requests.post(post_url, json=post_data, headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        })

        if post_response.status_code == 201:
            return "Post successfully published to LinkedIn!"
        else:
            return f"Failed to post: {post_response.text}", 400

    return render_template("post.html")


if __name__ == "__main__":
    app.run(debug=True)
