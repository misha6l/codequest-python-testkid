async function loadDashboard() {
    try {
        // Fetch data with Cache Buster to ensure we get the newest results
        const [identityRes, resultsRes] = await Promise.all([
            fetch(`identity.json?v=${Date.now()}`),
            fetch(`last_results.json?v=${Date.now()}`)
        ]);

        const identity = await identityRes.json();
        const data = await resultsRes.json();

        // Update Dashboard Header
        document.getElementById('xp-val').innerText = identity.xp;
        document.getElementById('rank-val').innerText = identity.rank || "Cadet";
        
        const list = document.getElementById('checklist');
        list.innerHTML = ""; 

        // Build checklist with "Scanning" effect
        data.results.forEach((item, index) => {
            setTimeout(() => {
                const li = document.createElement('li');
                li.className = item.pass ? 'pass' : 'fail';
                li.innerHTML = `<span>${item.pass ? '✓' : '✗'}</span> <strong>${item.req}</strong>: ${item.feedback}`;
                list.appendChild(li);
            }, index * 300); 
        });

        // Handle Routing if All Requirements Pass
        if (data.allPass === true || data.allPass === "true") {
            setTimeout(() => {
                document.getElementById('mission-status').innerText = "MISSION ACCOMPLISHED";
                document.getElementById('next-assignment').classList.remove('hidden');
                
                // Click events for the 3 routes
                const cards = document.querySelectorAll('.route-card');
                if (cards.length >= 3) {
                    cards[0].onclick = () => window.location.href = 'mission-warrior.html';
                    cards[1].onclick = () => window.location.href = 'mission-architect.html';
                    cards[2].onclick = () => window.location.href = 'mission-explorer.html';
                }
            }, data.results.length * 350);
        } else {
            document.getElementById('mission-status').innerText = "SYSTEM REPAIRS REQUIRED";
        }

    } catch (e) {
        console.error("Dashboard Error:", e);
        document.getElementById('mission-status').innerText = "OFFLINE: CHECK JSON FILES";
    }
}

loadDashboard();
