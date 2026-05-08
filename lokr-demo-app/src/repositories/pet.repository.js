// Mock Database
let petsDb = [
    { id: '1', name: 'Fido', ownerId: '101' },
    { id: '2', name: 'Whiskers', ownerId: '102' }
];

class PetRepository {
    async deleteById(petId) {
        const initialLength = petsDb.length;
        petsDb = petsDb.filter(pet => pet.id !== petId);
        
        // Returns true if a pet was actually removed
        return petsDb.length < initialLength;
    }
}

module.exports = new PetRepository();
