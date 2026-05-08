const express = require('express');
const adminRoutes = require('./routes/admin.routes');
const petRoutes = require('./routes/pet.routes');
const { authenticate } = require('./middleware/auth');

const app = express();
app.use(express.json());

// VULNERABILITY: Unsafe admin route.
// Mounted BEFORE the `authenticate` middleware, making it publicly accessible.
// An agent tracing the execution flow should notice the mounting order flaw.
app.use('/api/admin', adminRoutes);

// Global authentication applied to all routes below this line
app.use(authenticate);

app.use('/api/pets', petRoutes);

const PORT = 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
