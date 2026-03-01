document.getElementById("claimForm").onsubmit = function(e) {
  e.preventDefault();

  document.getElementById("claimStatus").innerText =
    "Submitted – Under Review";

  alert("Claim submitted successfully!");
};

function updateClaimStatus(status) {
  const badge = document.getElementById("statusBadge");

  const submitted = document.getElementById("step-submitted");
  const verified = document.getElementById("step-verified");
  const approved = document.getElementById("step-approved");

  // Reset
  [submitted, verified, approved].forEach(step => {
    step.classList.remove("active", "completed");
  });

  badge.className = "status-badge";

  if (status === "pending") {
    badge.textContent = "Pending";
    badge.classList.add("pending");
    submitted.classList.add("active");
  }

  if (status === "verified") {
    badge.textContent = "Verified";
    badge.classList.add("verified");
    submitted.classList.add("completed");
    verified.classList.add("active");
  }

  if (status === "approved") {
    badge.textContent = "Approved";
    badge.classList.add("approved");
    submitted.classList.add("completed");
    verified.classList.add("completed");
    approved.classList.add("active");
  }

  if (status === "rejected") {
    badge.textContent = "Rejected";
    badge.classList.add("rejected");
  }
}

/* DEMO FLOW (auto animation) */
setTimeout(() => updateClaimStatus("pending"), 800);
setTimeout(() => updateClaimStatus("verified"), 3000);
setTimeout(() => updateClaimStatus("approved"), 5500);
