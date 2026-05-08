
function requireRole(requiredRole) {
    return (req, res, next) => {
        // Fails safely if req.user is undefined (e.g., when auth middleware is bypassed)
        if (!req.user || req.user.role !== requiredRole) {
            return res.status(403).json({ error: "Forbidden: Insufficient privileges" });
        }
        next();
    };
}

module.exports = { requireRole };
