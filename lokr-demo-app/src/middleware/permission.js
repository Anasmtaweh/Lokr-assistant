function checkAccess(req, res, next) {
    if (!req.user) {
        return res.status(401).json({ error: "Unauthorized" });
    }

    const isAdmin = req.user.role === 'admin';
    const hasPermission = req.user.permissions && req.user.permissions.includes('write');

    if (!isAdmin || !hasPermission) {
        return res.status(403).json({ error: "Access Denied" });
    }

    next();
}

module.exports = { checkAccess };
