
const petService = require('../services/pet.service');

class PetController {
    async deletePet(req, res) {
        try {
            const petId = req.params.id;
            const userId = req.user.id; // Extracted from auth middleware
            
            // Passes both petId and userId down the dependency chain
            const result = await petService.removePet(petId, userId);
            
            if (!result) return res.status(404).json({ error: "Pet not found" });
            res.json({ message: 'Pet deleted successfully' });
        } catch (error) {
            res.status(500).json({ error: "Internal server error" });
        }
    }
}

module.exports = new PetController();

