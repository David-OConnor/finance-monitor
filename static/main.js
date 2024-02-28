const FETCH_HEADERS_GET = {
    method: "GET",
    mode: "cors",
    credentials: "same-origin",
    headers: {
        "X-CSRFToken": getCrsfToken(),
        Accept: "application/json",
    },
}
const FETCH_HEADERS_POST = {
    method: "POST",
    mode: "cors",
    credentials: "same-origin",
    headers: {
        "X-CSRFToken": getCrsfToken(),
        Accept: "application/json",
    },
}

let LINK_TOKEN = ""



function getPublicToken() {
    console.log("Getting public token. Link token: ", LINK_TOKEN)
    let handler = Plaid.create({
        // Create a new link_token to initialize Link
        // token: await fetch("/create_link_token", {...FETCH_HEADERS_POST }).link_token,
        token: LINK_TOKEN,
        onLoad: function() {
            console.log("Link loaded")
            // Optional, called when Link loads
        },
        onSuccess: function(public_token, metadata) {
            // Send the public_token to your app server.
            // The metadata object contains info about the institution the
            // user selected and the account ID or IDs, if the
            // Account Select view is enabled.
            // $.post('/exchange_public_token', {
            //     public_token: public_token,
            // });
            //
            console.log("Received a public token; sending to the backend.")

            fetch("/exchange-public-token", { body: JSON.stringify({pulic_token: public_token}), ...FETCH_HEADERS_POST })
                // Parse JSON if able.
                .then(result => {
                    try {
                        return result.json();
                    }
                    catch (e) {
                        console.error("Error parsing JSON: ", e)
                    }
                })
                .then(r => {
                    let linkToken = r.link_token
                    console.log("Received link token: ", linkToken)
                });
        },
        onExit: function(err, metadata) {
            console.log("Link flow exited")
            // The user exited the Link flow.
            if (err != null) {
                // The user encountered a Plaid API error prior to exiting.
            }
            // metadata contains information about the institution
            // that the user selected and the most recent API request IDs.
            // Storing this information can be helpful for support.
        },
        onEvent: function(eventName, metadata) {
            console.log("Link flow event: ", eventName)
            console.log("Metadata: ", metadata)
            // Optionally capture Link flow events, streamed through
            // this callback as your users connect an Item to Plaid.
            // For example:
            // eventName = "TRANSITION_VIEW"
            // metadata  = {
            //   link_session_id: "123-abc",
            //   mfa_type:        "questions",
            //   timestamp:       "2017-09-14T14:42:19.350Z",
            //   view_name:       "MFA",
            // }
        }
    });

    handler.open();
}

function getCrsfToken() {
    // For CRSF compatibility
    let name_ = "csrftoken"
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name_.length + 1) === (name_ + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name_.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

btn = document.getElementById("token_exchange")
btn.addEventListener("click", e => {
    postData = {}

    const url = "/create-link-token"
    fetch(url, { body: JSON.stringify(postData), ...FETCH_HEADERS_POST })
        // Parse JSON if able.
        .then(result => {
            try {
                return result.json();
            }
            catch (e) {
                console.error("Error parsing JSON: ", e)
            }
        })
        .then(r => {
            LINK_TOKEN = r.link_token
            console.log("Link token set: ", LINK_TOKEN)
        });
})

let handler = null
const btnPublic = document.getElementById("link-button")
btnPublic.addEventListener("click", _ => {
    console.log("CLICK")
    getPublicToken()
});