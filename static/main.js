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

// Global mutal variables
let LINK_TOKEN = ""
let SEARCH_TEXT = ""

// Includes all loaded transactions
let TRANSACTIONS = []
let TRANSACTIONS_DISPLAYED = []




function getPublicToken() {
    // Launches a Plaid-controlled window to link to an account, using an already-retrieved link token.
    // After the user enters information, sends the public token to the backend, which exchanges it for
    // an access token. This is then stored in the database, associated with the user's account at
    // the linked institution.

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
            console.log("Metadata: ", metadata)

            const payload = {
                public_token: public_token,
                metadata: metadata
            }

            fetch("/exchange-public-token", { body: JSON.stringify(payload), ...FETCH_HEADERS_POST })
                .then(result => result.json())
                .then(r => {
                    if (r.success) {
                        console.log("Token exchange complete")
                    } else {
                        console.error("Token exchange failed")
                    }
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

function refreshBalances() {
    fetch("/refresh-alances", FETCH_HEADERS_GET)
        // Parse JSON if able.
        .then(result => result.json())
        .then(r => {
            if (!r.updated) {
                return
            }

            let div = document.getElementById("balances")
            div.innerHTML = ""
        });
}

function refreshTransactions(searchText) {
    // todo DRY with balance refresh

    // fetch("/refresh-transactions", FETCH_HEADERS_GET)
    //     // Parse JSON if able.
    //     .then(result => result.json())
    //     .then(r => {
    //         if (!r.updated) {
    //             return
    //         }

    let table = document.getElementById("transactions")
    table.replaceChildren();


    let transactions
    // todo: Use TRANSACTIONS_DISPLAYED?
    // Note: This truthy statement catches both an empty string, and an undefined we get on init.
    if (!searchText) {
        transactions = TRANSACTIONS
    } else {
        transactions = TRANSACTIONS.filter(t => {
            console.log(t, searchText)
            return t.description.toLowerCase().includes(searchText) || t.notes.toLowerCase().includes(searchText)
            // todo: Description search as well
        })
    }


    for (let tran of transactions) {
        const row = document.createElement("tr")

        let col = document.createElement("td")
        col.textContent = tran.categories
        row.appendChild(col)

        // todo: Fn.
        col = document.createElement("td")
        col.classList.add("transaction-cell")
        let h = document.createElement("h4")
        h.classList.add("tran-heading")
        h.textContent = tran.description
        h.style.fontWeight = "normal"
        col.appendChild(h)

        row.appendChild(col)

        col = document.createElement("td")
        col.classList.add("transaction-cell")
        h = document.createElement("h4")
        h.classList.add("tran-heading")
        h.textContent = tran.notes
        h.style.fontWeight = "normal"
        h.style.color = "#444444"
        col.appendChild(h)

        row.appendChild(col)

        col = document.createElement("td")
        col.classList.add("transaction-cell")
        h = document.createElement("h4")
        h.classList.add("tran-heading")
        h.textContent = tran.amount
        h.classList.add(tran.amount_class)
        col.appendChild(h)

        row.appendChild(col)

        col = document.createElement("td")
        col.classList.add("transaction-cell")
        h = document.createElement("h4")
        h.classList.add("tran-heading")
        h.textContent = tran.date_display
        col.appendChild(h)

        row.appendChild(col)

        table.appendChild(row)
    }
    // {% for tran in transactions %}
    // <tr class="transaction">
    //     <td class="transaction-cell"><h4 class="tran-heading">{{ tran.categories}}</h4></td>
    //     <td class="transaction-cell"><h4 class="tran-heading" style="font-weight: normal;">{{ tran.description }}</h4></td>
    //     <td class="transaction-cell"><h4 class="tran-heading" style="font-weight: normal; color: #444444;">{{ tran.notes }}</h4></td>
    //     <td class="{{ tran.amount_class }} transaction-cell"><h4 class="tran-heading">{{ tran.amount }}</h4></td>
    //     <td class="transaction-cell"><h4 class="tran-heading">{{ tran.date_display }}</h4></td>
    // </tr>
    // {% endfor %}

    // });
}

function updateSearch() {
    // SEARCH_TEXT = document.getElementById("search").value
    const searchText = document.getElementById("search").value.toLowerCase()
    refreshTransactions(searchText)
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

function init() {
    // We run this on page load
    document.getElementById("link-button").addEventListener("click", _ => {
        fetch("/create-link-token", FETCH_HEADERS_GET)
            // Parse JSON if able.
            .then(result => result.json())
            .then(r => {
                LINK_TOKEN = r.link_token
                console.log("Link token set: ", LINK_TOKEN)
                getPublicToken()
            });
    });

    document.getElementById('export').addEventListener('click', function() {
        window.location.href = '/export'
    })

    document.getElementById('export').addEventListener('click', function() {
        window.location.href = '/export'
    })

    const importStart = document.getElementById('import-start')
    importStart.addEventListener('click', function() {
        // importStart.
        const importForm = document.getElementById("import-form")
        if (importForm.style.visibility === "hidden") {
            importForm.style.visibility = "visible"
        } else {
            importForm.style.visibility = "hidden"
        }

    })

    // Load transactions from the backend.
    // fetch("/load-transactions", FETCH_HEADERS_POST)
    fetch("/load-transactions", { body: JSON.stringify({}), ...FETCH_HEADERS_POST })
        // Parse JSON if able.
        .then(result => result.json())
        .then(r => {
            TRANSACTIONS = r.transactions
            TRANSACTIONS_DISPLAYED = r.transactions
            refreshTransactions()
        });
}

init()

