async function loadDashboard() {
    try {
        // Fetch student data and mission results
        const [identityRes, resultsRes] = await Promise.all([
            fetch('identity.json'),
            fetch('last_results.json')
        ]);

        const identity = await identityRes.json();
        const data = await resultsRes.json();

        // Update Dashboard Header
        document.getElementById('xp-val').innerText = identity.xp;
        document.getElementById('rank-val').innerText = identity.rank || "Cadet";
        
        const list = document.getElementById('checklist');
        list.innerHTML = ""; 

        // Build checklist with a small delay for "Scanning" effect
        data.results.forEach((item, index) => {
            setTimeout(() => {
                const li = document.createElement('li');
                li.className = item.pass ? 'pass' : 'fail';
                li.style.animation = "fadeIn 0.5s forwards";
                li.innerHTML = `<span>${item.pass ? '✓' : '✗'}</span> <strong>${item.req}</strong>: ${item.feedback}`;
                list.appendChild(li);
            }, index * 300); 
        });

        // Handle Routing if All Requirements Pass
        if (data.allPass) {
            setTimeout(() => {
                document.getElementById('mission-status').innerText = "MISSION ACCOMPLISHED";
                document.getElementById('next-assignment').classList.remove('hidden');
                
                // Map buttons to the destination pages
                const cards = document.querySelectorAll('.route-card');
                cards[0].onclick = () => window.location.href = 'mission-warrior.html';
                cards[1].onclick = () => window.location.href = 'mission-architect.html';
                cards[2].onclick = () => window.location.href = 'mission-explorer.html';
            }, data.results.length * 350);
        } else {
            document.getElementById('mission-status').innerText = "SYSTEM REPAIRS REQUIRED";
        }

    } catch (e) {
        console.error("Dashboard Error:", e);
        document.getElementById('mission-status').innerText = "WAITING FOR UPLINK...";
    }
}

loadDashboard();
