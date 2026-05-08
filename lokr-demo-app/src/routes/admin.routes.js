const router = require('express').Router();
const { requireRole } = require('../middleware/role');

// Unprotected endpoint due to app.js mounting order
router.get('/system-logs', (req, res) => {
    res.json({ logs: ["System started", "Database connected", "Root login detected"] });
});

// VULNERABILITY: Role deadlock.
// Middleware chain strictly requires the role to be 'user' and then strictly 'admin'.
// This creates an unreachable execution path (a user cannot have both roles simultaneously).
router.post('/wipe-database', 
    requireRole('user'), 
    requireRole('admin'), 
    (req, res) => {
        res.json({ message: "Database wiped successfully." });
    }
);

module.exports = router;
