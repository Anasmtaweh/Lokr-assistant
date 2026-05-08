
const router = require('express').Router();
const petController = require('../controllers/pet.controller');

// Demonstrates cross-file dependency chain starting here
router.delete('/:id', petController.deletePet);

module.exports = router;
