// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SchnorrBatchVerification {

    mapping(string => bool) public schnorrProofVerified;
    mapping(string => uint256) public didToIndex;

    event DebugVerification(string step, uint256 R, uint256 s, uint256 challenge, bool proofVerified, string studentDid);
    event DebugVCVerification(bool vcVerified, string hashedVCFromVP, string ipfsHashedVC);
    event DebugSchnorrValues(uint256 lhs, uint256 rhs, bool result, uint256 R, uint256 s, uint256 g, uint256 p, uint256 c, string emailHashed);
    event DebugFailure(string message);

    function storeDidToIndex(string memory studentDid, uint256 index) public {
        didToIndex[studentDid] = index;
    }

    function getIndexByDid(string memory studentDid) public view returns (uint256) {
        return didToIndex[studentDid];
    }

    function getChallenge(uint256 R) public view returns (uint256) {
        return uint256(keccak256(abi.encodePacked(R, block.timestamp))) % 23;
    }

    function verify(
        uint256 R, 
        uint256 s, 
        uint256 g, 
        uint256 p, 
        uint256 c, 
        string memory employerHashedEmail, 
        string memory hashedVCFromVP, 
        string memory studentDid, 
        string memory ipfsHashedVC
    ) public returns (bool) {
        emit DebugVerification("Starting Schnorr proof verification", R, s, c, false, studentDid);

        if (!schnorrProofVerified[studentDid]) {
            bool schnorrResult = verifySchnorrProof(R, s, g, p, c, employerHashedEmail);
            if (!schnorrResult) {
                emit DebugFailure("Schnorr proof verification failed");
                return false;
            }
            schnorrProofVerified[studentDid] = true;

            emit DebugVerification("Schnorr proof verified", R, s, c, true, studentDid);
        }

        emit DebugVerification("Starting VC verification", R, s, c, true, studentDid);
        
        bool vcVerified = verifyHashedVC(hashedVCFromVP, ipfsHashedVC);
        if (!vcVerified) {
            emit DebugFailure("Hashed VC verification failed");
            emit DebugVCVerification(false, hashedVCFromVP, ipfsHashedVC);
            return false;
        }
        
        emit DebugVCVerification(true, hashedVCFromVP, ipfsHashedVC);
        return true;
    }

    function verifySchnorrProof(
        uint256 R, 
        uint256 s, 
        uint256 g, 
        uint256 p, 
        uint256 c, 
        string memory employerHashedEmail
    ) internal returns (bool) {
        uint256 lhs = modExp(g, s, p);
        uint256 rhs = calculateRHS(R, g, c, employerHashedEmail, p);

        bool proofResult = lhs == rhs;
        emit DebugSchnorrValues(lhs, rhs, proofResult, R, s, g, p, c, employerHashedEmail);  // Log all relevant values

        return proofResult;
    }

    function verifyHashedVC(
        string memory hashedVCFromVP, 
        string memory ipfsHashedVC
    ) public pure returns (bool) {
        return keccak256(abi.encodePacked(hashedVCFromVP)) == keccak256(abi.encodePacked(ipfsHashedVC));
    }

    function modExp(uint256 base, uint256 exp, uint256 mod) internal pure returns (uint256) {
        uint256 result = 1;
        while (exp > 0) {
            if (exp % 2 == 1) {
                result = (result * base) % mod;
            }
            base = (base * base) % mod;
            exp /= 2;
        }
        return result;
    }

    function calculateRHS(
        uint256 R, 
        uint256 g, 
        uint256 c, 
        string memory employerHashedEmail, 
        uint256 p
    ) internal pure returns (uint256) {
        uint256 x = uint256(keccak256(abi.encodePacked(employerHashedEmail)));
        uint256 g_cx = modExp(g, c * x, p);
        return (R * g_cx) % p;
    }
}
