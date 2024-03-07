function isValidNumber(str) {
    // First, try parsing the string
    const num = parseFloat(str);

    // Check if the parsed number is NaN. If so, it's not a valid number.
    if (isNaN(num)) {
        return false;
    }

    // Then check if the string representation of the parsed number matches the input.
    // This ensures that inputs like "123abc" or "123.45.67" are rejected.
    // Trim the input to ignore leading/trailing whitespace.
    const trimmedInput = str.trim();

    // Create a regular expression to match the possible string representations of the parsed number.
    // This accounts for both integer and floating-point numbers, including those in exponential notation.
    const regexPattern = new RegExp("^" + num + "$|^" + num + "e[+-]?\\d+$", "i");

    // Test the trimmed input against the regular expression.
    return regexPattern.test(trimmedInput);
}

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

function accTypeFromNum(val) {
    // See models.py
    if (val === 0) {
        return "Checking"
    }
    if (val === 1) {
        return "Savings"
    }
    if (val === 2) {
        return "Debit"
    }
    if (val === 3) {
        return "Credit"
    }
    if (val === 4) {
        return "401K"
    }
    if (val === 5) {
        return "Student"
    }
    if (val === 6) {
        return "Mortgage"
    }
    if (val === 7) {
        return "Cd"
    }
    if (val === 8) {
        return "Money market"
    }
    if (val === 9) {
        return "IRA"
    }
    if (val === 10) {
        return "Mutual fund"
    }
    if (val === 11) {
        return "Crypto"
    }

    if (val === 12) {
        return "Asset"
    }

    if (val === 13) {
        return "Brokerage"
    }

    if (val === 14) {
        return "Roth"
    }
}
