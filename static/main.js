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
let VALUE_THRESH = 0

const PAGE_SIZE = 60

// todo: Config object?

// Includes all loaded transactions
let TRANSACTIONS = []
let TRANSACTIONS_DISPLAYED = []
let TRANSACTION_ICONS = true
let EDIT_MODE_TRAN = false
let EDIT_MODE_ACC = false

// We use an object vice map for serialization compatibility.
let TRANSACTIONS_UPDATED = {}
let ACCOUNTS_UPDATED = {}


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

function filterTransactions() {
    const searchText = SEARCH_TEXT
    const valueThresh = VALUE_THRESH

    let transactions
    // todo: Use TRANSACTIONS_DISPLAYED?
    // Note: This truthy statement catches both an empty string, and an undefined we get on init.
    if (!searchText) {
        transactions = TRANSACTIONS
    } else {
        transactions = TRANSACTIONS.filter(t => {
            return t.description.toLowerCase().includes(searchText) ||
                t.notes.toLowerCase().includes(searchText) ||
                t.categories.toLowerCase().includes(searchText)
        })
    }

    if (valueThresh) {
        transactions = transactions.filter(t => Math.abs(t.amount) >= valueThresh)
    }

    transactions.sort((b, a) => new Date(a.date) - new Date(b.date))

    return transactions
}

function refreshTransactions() {
    let transactions = filterTransactions()

    let tbody = document.getElementById("transaction-tbody")
    tbody.replaceChildren();

    // todo: thead and tbody els?
    //
    // // todo: We don't need to recreate the TH each time.
    // const head = createEl("tr", {}, {height: "40px", borderBottom: "2px solid black"}, "")
    // let col = createEl("th", {"class": "transaction-cell"}, {}, "")
    //
    // let div = createEl("div", {}, {display: "flex", alignItems: "center"}, "")
    // let h = createEl("h4", {class: "tran-heading"}, {}, "Icons")

    // todo: form to add a new transaction.

    // // todo: Store to the DB
    // let check = createEl("input", {type: "checkbox"}, {}, "")
    // if (TRANSACTION_ICONS) {
    //     check.setAttribute("checked", null)
    // }

    // check.setAttribute("checked", TRANSACTION_ICONS)

    console.log("Refreshing transactions.")

    // div.appendChild(h)
    // div.appendChild(check)
    // col.appendChild(div)

    // head.appendChild(col)


    for (let tran of transactions) {
        const row = document.createElement("tr")

        let col = document.createElement("td")

        if (TRANSACTION_ICONS) {
            col.textContent = tran.categories_icon
        } else {
            col.textContent = tran.categories
        }
        row.appendChild(col)

        col = createEl("td", {class: "transaction-cell"})
        let h = createEl("h4", {class: "tran-heading"}, {fontWeight: "normal"}, tran.description)
        col.appendChild(h)

        row.appendChild(col)

        col = createEl("td", {class: "transaction-cell"})
        if (EDIT_MODE_TRAN) {
            h = createEl("input", {id: "edit-notes:" + tran.id, value: tran.notes}, {marginRight: "30px"})

            h.addEventListener("input", e => {
                let updated = {
                    ...tran,
                    notes: e.target.value
                }
                // todo: DRY!
                TRANSACTIONS_UPDATED[String(tran.id)] = updated
            })
        } else {
            h = createEl("h4", {class: "tran-heading"}, {fontWeight: "normal", color: "#444444", marginRight: "60px"}, tran.notes)
        }

        col.appendChild(h)

        row.appendChild(col)

        col = createEl("td", {class: "transaction-cell"})
        if (EDIT_MODE_TRAN) {
            h = createEl("input", {id: "edit-amount:" + tran.id, value: tran.amount},
                {width: "80px", textAlign: "right", marginRight: "30px"}, "")
        } else {
            h = createEl("h4", {class: "tran-heading " +  tran.amount_class}, {}, tran.amount)
        }

        col.appendChild(h)

        row.appendChild(col)

        col = createEl("td", {class: "transaction-cell"})
        if (EDIT_MODE_TRAN) {
            h = createEl("input", {id: "edit-date:" + tran.id,type: "date", value: tran.date}, {width: "120px"})

            h.addEventListener("input", e => {
                let updated = {
                    ...tran,
                    date: e.target.value
                }
                // todo: DRY!
                TRANSACTIONS_UPDATED[String(tran.id)] = updated
            })
        } else {
            h = createEl("h4", {class: "tran-heading"}, {}, tran.date_display)
        }
        col.appendChild(h)

        row.appendChild(col)

        tbody.appendChild(row)
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

    // todo: Enforce integer value.
    let valueThresh = document.getElementById("transaction-value-filter").value
    // Remove non-integer values

    // todo: number field here is actually interfering, returning an empty string if invalid;
    // so, we can't just ignore chars.

    VALUE_THRESH = parseInt(valueThresh.replace(/\D+/g, ''))
    refreshTransactions()
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

function addAccountManual() {
    // We use this when submitting a new manual account
    // document.getElementById("add-account-manaul").addEventListener("click", _ => {
    //                 <input id="add-manual-name" />
    //
    //                 <select id="add-manual-type" style="border: 1px solid black; height: 32px; width: 156px;">
    //
    //                 <input id="add-manual-current" type="number" value="0" />

    // todo: Validate no blank account name
    const data = {
        name: document.getElementById("add-manual-name").value,
        sub_type: parseInt(document.getElementById("add-manual-type").value),
        current: parseInt(document.getElementById("add-manual-current").value),
        iso_currency_code: document.getElementById("add-manual-currency-code").value,
    }

    fetch("/add-account-manual", {body: JSON.stringify(data), ...FETCH_HEADERS_POST})
        .then(result => result.json())
        .then(r => {
            console.log(r)
            // todo: Handle a failure.
        });

    let form = document.getElementById("add-manual-form")
    let btn = document.getElementById("add-manual-button")
    form.style.visibility = "collapse"
    btn.textContent = "➕ Manual account"
}

function setupEditTranButton() {
    let btn = document.getElementById("edit-transactions");

    btn.addEventListener("click", _ => {
        if (EDIT_MODE_TRAN) {
            // Save transactions on click

            const data = {
                // Discard keys; we mainly use them for updating internally here.
                transactions: Object.values(TRANSACTIONS_UPDATED)
            }

            // Save transactions to the database.
            fetch("/edit-transactions", { body: JSON.stringify(data), ...FETCH_HEADERS_POST })
                .then(result => result.json())
                .then(r => {
                    if (!r.success) {
                        console.error("Transaction save failed")
                    }
                });

            // Update transactions in place, so a refresh isn't required.
            for (let tran of Object.values(TRANSACTIONS_UPDATED)) {
                let date = new Date(tran.date)
                tran.date_display = (date.getUTCMonth() + 1) % 12 + "/" + date.getUTCDate()
                TRANSACTIONS = [
                    ...TRANSACTIONS.filter(t => t.id !== tran.id),
                    tran,
                ]
            }

            TRANSACTIONS_UPDATED = {}

            refreshTransactions()  // Overkill; just to taek out of edit mode. todo: SPlit refreshTransactions.
            EDIT_MODE_TRAN = false
            btn.textContent = "Edit transactions"
        } else {
            // Enable editing on click.
            refreshTransactions()  // Overkill; just to taek out of edit mode. todo: SPlit refreshTransactions.
            EDIT_MODE_TRAN = true
            btn.textContent = "Save transactions"
        }
        refreshTransactions()
    })
}

// todo: DRY with tran edit setup
function setupEditAccsButton() {
    let btn = document.getElementById("edit-accounts");
    let section = document.getElementById("edit-accs-section")


    btn.addEventListener("click", _ => {
        if (EDIT_MODE_ACC) {
            // Save transactions on click

            const data = {
                // Discard keys; we mainly use them for updating internally here.
                accounts: Object.values(ACCOUNTS_UPDATED)
            }

            // Save transactions to the database.
            fetch("/edit-accounts", { body: JSON.stringify(data), ...FETCH_HEADERS_POST })
                .then(result => result.json())
                .then(r => {
                    if (!r.success) {
                        console.error("Account edits save failed")
                    }
                });

            // todo: As long as we're using the template, consider a page refresh.

            // Update accounts in place, so a refresh isn't required.
            // todo: A/R
            // for (let acc of Object.values(ACCOUNTS_UPDATED)) {
            //     TRANSACTIONS = [
            //         ...TRANSACTIONS.filter(t => t.id !== acc.id),
            //         acc,
            //     ]
            // }

            ACCOUNTS_UPDATED = {}

            // todo: Refresh accounts.
            EDIT_MODE_ACC = false
            btn.textContent = "Edit accounts"
        } else {
            section.replaceChildren()

            // todo: Refresh accounts.
            // Enable editing on click.
            EDIT_MODE_ACC = true
            btn.textContent = "Save accounts"
        }
        refreshTransactions()
    })
}

// todo; Account an account type.
function setupAccForm(acc) {
    // Setup the form for adding and editing accounts.
    let form = document.getElementById("account-form")
    form.replaceChildren()

    let d, h, ip

    d = createEl("div", {}, {textAlign: "center"})
    h = createEl("h2", {}, {marginTop: 0, marginBottom: 18}, "Edit an account")
    d.appendChild(h)
    form.appendChild(d)

    d = createEl("div", {}, {alignItems: "center", justifyContent: "space-between"})
    h = createEl("h3", {value: acc.name}, {marginTop: 0, marginBottom: 18}, "Account name")
    ip = createEl("input")

    ip.addEventListener("change", e => {
        let updated = {
            ...acc,
            name: e.target.value
        }
        ACCOUNTS_UPDATED[acc.id] = updated
    })

    d.appendChild(h)
    d.appendChild(ip)
    form.appendChild(d)



                // <div style="display: flex; align-items: center; justify-content: space-between;">
                //     <h3>Type</h3>
                //     {#                    todo: DRY #}
                //     <select id="add-manual-type" style="border: 1px solid black; height: 32px; width: 156px;">
                //         <option value="0">Checking</option>
                //         <option value="1">Savings</option>
                //         <option value="2">Debit card</option>
                //         <option value="3">Credit card</option>
                //         <option value="4">401K</option>
                //         <option value="5">Student</option>
                //         <option value="6">Mortgage</option>
                //         <option value="7">CD</option>
                //         <option value="8">Money market</option>
                //         <option value="9">IRA</option>
                //         <option value="10">Mutual fund</option>
                //         <option value="11">Crypto</option>
                //         <option value="12">Asset (misc)</option>
                //         <option value="13">Brokerage</option>
                //         <option value="14">Roth</option>
                //     </select>
                // </div>


        d = createEl("div", {}, {alignItems: "center", justifyContent: "space-between"})
    h = createEl("h3", {}, {marginTop: 0, marginBottom: 18}, "Currency code")
    ip = createEl("input", {value: acc.iso_currency_code, maxLength: "3"})
    d.appendChild(h)
    d.appendChild(ip)
    form.appendChild(d)

    d = createEl("div", {}, {alignItems: "center", justifyContent: "space-between"})
    h = createEl("h3", {}, {}, "Value")
    ip = createEl("input", {type: "number", value: acc.current})
    d.appendChild(h)
    d.appendChild(ip)
    form.appendChild(d)


                // <div style="display: flex; align-items: center; justify-content: space-between;">
                //     <h3>Value (Must be updated manually)</h3>
                //     <input id="add-manual-current" type="number" value="0" />
                // </div>
                //
                // <div style="display: flex; justify-content: center; margin-top: 18px;">
                //     <button
                //             type="button"
                //             onClick="addAccountManual()"
                //             className="button-general" style="width: 140px;"
                //     >
                //         Add this account</button>
                // </div>

    console.log(form, "FORM")
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

    console.log("Loading transactions...")
    // Load transactions from the backend.
    // fetch("/load-transactions", FETCH_HEADERS_POST)
    fetch("/load-transactions", { body: JSON.stringify({}), ...FETCH_HEADERS_POST })
        // Parse JSON if able.
        .then(result => result.json())
        .then(r => {
            TRANSACTIONS = r.transactions
            // TRANSACTIONS_DISPLAYED = r.transactions
            refreshTransactions()
        });

    let check = document.getElementById("icon-checkbox")
    check.addEventListener("click", _ => {
        TRANSACTION_ICONS = !TRANSACTION_ICONS
        refreshTransactions() // todo: Dangerous potentially re infinite recursions, but seems to be OK.
    })

    setupEditTranButton()
    setupEditAccsButton()

    // // todo: Temp here. Move appropriately
    // let acc = {
    //     id: 0,
    //     name: "test_acc",
    //     type: 3,
    //     iso_currency_code: "GBP",
    //     current: 335,
    // }
    // setupAccForm(acc)
}

init()

// todo: util.js
function createEl(tag, attributes, style, text) {
    // Create and return an element with given attributes and style.
    let el = document.createElement(tag)

    if (attributes) {
        for (const [attr, val] of Object.entries(attributes)) {
            el.setAttribute(attr, val)
        }
    }

    if (style) {
        for (const [attr, val] of Object.entries(style)) {
            el.style[attr] = val
        }
    }

    if (text) {
        el.textContent = text
    }

    return el
}

function toggleAddManual() {
    let form = document.getElementById("add-manual-form")
    let btn = document.getElementById("add-manual-button")

    if (form.style.visibility === "visible") {
        form.style.visibility = "collapse"
        btn.textContent = "➕ Manual account"
    } else {
        form.style.visibility = "visible"
        btn.textContent = "(Cancel adding this account)"
    }

}