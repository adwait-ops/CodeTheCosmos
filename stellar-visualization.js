let scene, camera, renderer, controls, starMesh, starLight;

init();
for (let i = 0; i <= 200; i++) createStarfield();
animate();

function init() {
    // Grab the canvas container from HTML
    const container = document.getElementById("canvas-container");

    // Create the scene
    scene = new THREE.Scene();

    // Add a camera
    camera = new THREE.PerspectiveCamera(
        60, // FOV
        container.clientWidth / container.clientHeight, // aspect ratio
        0.1, // near clipping
        1000 // far clipping 
    );
    camera.position.set(0, 0, 30);

    // Init grid
    const gridHelperx = new THREE.GridHelper(container.clientHeight, container.clientHeight / 2);
    gridHelperx.rotation.x = Math.PI / 2;

    const gridHelpery = new THREE.GridHelper(container.clientHeight, container.clientHeight / 2);
    gridHelpery.rotation = (0, Math.PI / 2, 0);

    const gridHelperz = new THREE.GridHelper(container.clientHeight, container.clientHeight / 2);
    gridHelperz.rotation.z = Math.PI / 2;

    // === renderer ===
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    // === orbit controls (for rotation) and configure properly ===
    controls = new THREE.OrbitControls(camera, renderer.domElement);

    // === Background ===
    const spaceTexture = new THREE.TextureLoader().load('textures/starfield-1.jpg');
    scene.background = spaceTexture;

    // === Star(s) ===

    const starColor = 0xf2ed88
    const textureLoader = new THREE.TextureLoader();
    const starTexture = textureLoader.load('texture.jpg');
    const starMaterial = new THREE.MeshStandardMaterial({
        map: starTexture,
        emissive: 0xb70000, // gives a warm star glow
        emissiveIntensity: 1.5,
        color: starColor,    // overall star color
    });

    const starGeometry = new THREE.SphereGeometry(2, 128, 128); //1st para indicates radius

    starMesh = new THREE.Mesh(starGeometry, starMaterial);
    scene.add(starMesh, gridHelperz, gridHelperx, gridHelpery);

    // === also added a corona by using a transparent sphere ===
    const glowGeometry = new THREE.SphereGeometry(2.1, 128, 128);
    const glowMaterial = new THREE.MeshBasicMaterial({
        color: 0xffaa00,
        transparent: true,
        opacity: 0.5,
        blending: THREE.AdditiveBlending,
        side: THREE.BackSide,  // makes glow appear on the outside
    });

    const glowMesh = new THREE.Mesh(glowGeometry, glowMaterial);
    glowMesh.position.copy(starMesh.position);
    scene.add(glowMesh);

    // === Lighting ===
    starLight = new THREE.PointLight(0xffffff, 1, 100);
    starLight.position.set(5, 5, 5);
    scene.add(starLight);

    // === Resize Handling ===
    window.addEventListener("resize", onWindowResize);
}

function onWindowResize() {
    const container = document.getElementById("canvas-container");
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
    const gridHelperx = new THREE.GridHelper(container.clientHeight, container.clientHeight / 2);
    gridHelperx.rotation.x = Math.PI / 2;

    const gridHelpery = new THREE.GridHelper(container.clientHeight, container.clientHeight / 2);
    gridHelpery.rotation = (0, Math.PI / 2, 0);


    const gridHelperz = new THREE.GridHelper(container.clientHeight, container.clientHeight / 2);
    gridHelperz.rotation.z = Math.PI / 2;
}

function createStarfield() {
    const geometry = new THREE.SphereGeometry(0.175, 24, 24);
    const material = new THREE.MeshBasicMaterial({ color: 0xffffff })
    const star = new THREE.Mesh(geometry, material);

    const [x, y, z] = Array(3).fill().map(() => THREE.MathUtils.randFloatSpread(100));
    star.position.set(x, y, z);
    scene.add(star);
}

function animate() {
    requestAnimationFrame(animate);

    // Slight rotation for a lively look
    starMesh.rotation.y += 0.01;
    starMesh.rotation.z += 0.02;

    controls.update();
    renderer.render(scene, camera);
}

