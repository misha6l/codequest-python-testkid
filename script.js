async function loadDashboard() {
    try {
        // Fetch student data and mission results
        const [identityRes, resultsRes] = await Promise.all([
            fetch('identity.json'),
            fetch('last_results.json')
        ]);

        const identity = await identityRes.json();
        const data = await resultsRes.json();

        // Update Stats
        document.getElementById('xp-val').innerText = identity.xp;
        
        const list = document.getElementById('checklist');
        list.innerHTML = ""; // Clear loader

        // Build checklist from AI data
        data.results.forEach(item => {
            const li = document.createElement('li');
            li.className = item.pass ? 'pass' : 'fail';
            li.innerHTML = `${item.pass ? '✓' : '✗'} <strong>${item.req}</strong>: ${item.feedback}`;
            list.appendChild(li);
        });

        if (data.allPass) {
            document.getElementById('mission-status').innerText = "MISSION ACCOMPLISHED";
            document.getElementById('next-assignment').classList.remove('hidden');
        } else {
            document.getElementById('mission-status').innerText = "SYSTEM REPAIRS REQUIRED";
        }

    } catch (e) {
        console.log("Waiting for mission data...", e);
    }
}

loadDashboard();
