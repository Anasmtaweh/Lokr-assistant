const jwt = require('jsonwebtoken');

// VULNERABILITY: Hardcoded secret. 
// Sensitive credentials placed directly in source code.
const JWT_SECRET = "super-secret-key-123";

function authenticate(req, res, next) {
    // VULNERABILITY: Debug backdoor.
    // Allows complete bypass of JWT authentication via a custom header.
    if (req.headers['x-debug-auth'] === 'true') {
        req.user = { id: 999, role: 'admin' };
        return next();
    }

    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: "No token provided" });

    try {
        const decoded = jwt.verify(token, JWT_SECRET);
        req.user = decoded;
        next();
    } catch (err) {
        res.status(401).json({ error: "Invalid token" });
    }
}

module.exports = { authenticate, JWT_SECRET };
