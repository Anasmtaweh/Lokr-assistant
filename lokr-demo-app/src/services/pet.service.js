
const petRepository = require('../repositories/pet.repository');

class PetService {
    async removePet(petId, userId) {
        // VULNERABILITY: Missing ownership validation.
        // The controller provides `userId`, but the service completely ignores it.
        // It blindly asks the repository to delete the record by ID.
        // This allows an authenticated user to delete another user's pet (IDOR).
        return await petRepository.deleteById(petId);
    }
}

module.exports = new PetService();
