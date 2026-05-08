
/**
 * MISLEADING IRRELEVANT FILE
 * Purposefully placed here to test the Lokr-agent's Graph-RAG precision. 
 * An intelligent agent should realize this file has no imports/exports related to 
 * the dependency chain, routes, or authentication flow, and ignore it during audits.
 */

function calculateCircleArea(radius) {
    if (radius < 0) throw new Error("Radius cannot be negative");
    return Math.PI * radius * radius;
}

function calculateHypotenuse(a, b) {
    return Math.sqrt(a * a + b * b);
}

module.exports = { calculateCircleArea, calculateHypotenuse };
