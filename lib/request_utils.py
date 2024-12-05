def make_headers(auth_token):
    return {
        "Authorization": auth_token,
        "Content-Type": "application/json",
        "Notion-Version": "2021-05-13"
    }