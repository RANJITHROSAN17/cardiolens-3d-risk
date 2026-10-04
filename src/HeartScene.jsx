import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const VESSEL_IDS = ['lad', 'lcx', 'rca'];
const VESSEL_PATHS = {
  lad: [
    [-0.02, 0.70, 0.285], [-0.02, 0.50, 0.315], [0.055, 0.28, 0.315],
    [0.03, 0.04, 0.315], [0.075, -0.22, 0.30], [0.015, -0.61, 0.24],
  ],
  lcx: [
    [-0.02, 0.66, 0.29], [-0.22, 0.62, 0.31], [-0.44, 0.54, 0.30],
    [-0.63, 0.36, 0.27], [-0.61, 0.15, 0.265], [-0.43, 0.03, 0.26],
  ],
  rca: [
    [0.01, 0.66, 0.29], [0.23, 0.61, 0.31], [0.47, 0.44, 0.30],
    [0.62, 0.19, 0.275], [0.52, -0.08, 0.27], [0.26, -0.27, 0.245],
  ],
};

function scoreColor(score) {
  if (!Number.isFinite(score)) return new THREE.Color('#9eabb4');
  const stops = [
    { at: 0, color: new THREE.Color('#2aa99a') },
    { at: 0.5, color: new THREE.Color('#e2b04a') },
    { at: 1, color: new THREE.Color('#d84d70') },
  ];
  const t = THREE.MathUtils.clamp(score, 0, 1);
  if (t <= 0.5) return stops[0].color.clone().lerp(stops[1].color, t * 2);
  return stops[1].color.clone().lerp(stops[2].color, (t - 0.5) * 2);
}

function makeTube(points, radius, color, parent, vesselId = null, pickables = []) {
  const curve = new THREE.CatmullRomCurve3(points.map(([x, y, z]) => new THREE.Vector3(x, y, z)));
  const geometry = new THREE.TubeGeometry(curve, 72, radius, 10, false);
  const material = new THREE.MeshStandardMaterial({
    color,
    emissive: color,
    emissiveIntensity: vesselId ? 0.22 : 0.06,
    roughness: 0.31,
    metalness: 0.04,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.userData.vesselId = vesselId;
  mesh.castShadow = false;
  mesh.receiveShadow = false;
  parent.add(mesh);
  if (vesselId) pickables.push(mesh);
  return mesh;
}

function scoreFor(results, id) {
  const value = results?.vessels?.[id]?.score;
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export default function HeartScene({ results, activeVessel, onVesselSelect }) {
  const hostRef = useRef(null);
  const meshRef = useRef({});
  const onSelectRef = useRef(onVesselSelect);

  useEffect(() => { onSelectRef.current = onVesselSelect; }, [onVesselSelect]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return undefined;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 40);
    camera.position.set(0, 0.08, 5.25);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.16;
    renderer.shadowMap.enabled = false;
    renderer.domElement.setAttribute('aria-label', 'Interactive schematic three-dimensional heart with selectable coronary arteries');
    renderer.domElement.setAttribute('role', 'img');
    host.appendChild(renderer.domElement);

    scene.add(new THREE.HemisphereLight(0xf5fbff, 0xd6e0e7, 2.0));
    const key = new THREE.DirectionalLight(0xffffff, 2.5);
    key.position.set(3.2, 4.2, 5.0);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0x85b8cc, 1.25);
    fill.position.set(-4, 0.8, 3.4);
    scene.add(fill);
    const rim = new THREE.PointLight(0xffb1bf, 7, 9);
    rim.position.set(0.3, 0.2, -2.2);
    scene.add(rim);

    const anatomy = new THREE.Group();
    anatomy.position.y = -0.02;
    scene.add(anatomy);

    // Procedural, schematic heart surface. This is illustrative geometry, not a patient mesh.
    const heartShape = new THREE.Shape();
    heartShape.moveTo(0, -1.06);
    heartShape.bezierCurveTo(0.16, -0.65, 0.96, -0.08, 0.86, 0.62);
    heartShape.bezierCurveTo(0.78, 1.13, 0.20, 1.18, 0, 0.73);
    heartShape.bezierCurveTo(-0.20, 1.18, -0.78, 1.13, -0.86, 0.62);
    heartShape.bezierCurveTo(-0.96, -0.08, -0.16, -0.65, 0, -1.06);
    heartShape.closePath();
    const heartGeometry = new THREE.ExtrudeGeometry(heartShape, {
      depth: 0.43,
      bevelEnabled: true,
      bevelSegments: 4,
      steps: 1,
      bevelSize: 0.065,
      bevelThickness: 0.055,
      curveSegments: 20,
    });
    heartGeometry.translate(0, 0, -0.215);
    const heartMaterial = new THREE.MeshPhysicalMaterial({
      color: '#a9405b',
      roughness: 0.58,
      metalness: 0.015,
      clearcoat: 0.18,
      clearcoatRoughness: 0.5,
    });
    const heart = new THREE.Mesh(heartGeometry, heartMaterial);
    heart.position.y = 0.01;
    anatomy.add(heart);

    // Great vessels add orientation cues without implying patient-specific anatomy.
    makeTube([
      [-0.06, 0.69, -0.08], [-0.09, 0.99, -0.07], [0.04, 1.17, -0.07],
      [0.30, 1.15, -0.07], [0.38, 0.89, 0.02],
    ], 0.095, '#cf6d78', anatomy);
    makeTube([
      [-0.06, 0.73, -0.08], [-0.29, 1.02, -0.10], [-0.50, 1.03, -0.10],
      [-0.54, 0.79, -0.02],
    ], 0.064, '#9c718d', anatomy);

    const pickables = [];
    const vesselMeshes = {};
    vesselMeshes.lad = makeTube(VESSEL_PATHS.lad, 0.036, '#50b5a7', anatomy, 'lad', pickables);
    vesselMeshes.lcx = makeTube(VESSEL_PATHS.lcx, 0.033, '#50b5a7', anatomy, 'lcx', pickables);
    vesselMeshes.rca = makeTube(VESSEL_PATHS.rca, 0.033, '#50b5a7', anatomy, 'rca', pickables);

    // Fine branches are visual texture only and inherit their parent vessel's current color.
    const branches = {
      lad: [
        [[0.025, 0.38, 0.31], [0.22, 0.30, 0.285], [0.34, 0.14, 0.26]],
        [[0.055, 0.00, 0.31], [-0.16, -0.10, 0.28], [-0.28, -0.26, 0.26]],
        [[0.06, -0.30, 0.29], [0.22, -0.43, 0.26], [0.31, -0.58, 0.22]],
      ],
      lcx: [
        [[-0.39, 0.55, 0.29], [-0.37, 0.72, 0.255], [-0.31, 0.82, 0.22]],
        [[-0.55, 0.31, 0.27], [-0.73, 0.25, 0.24], [-0.77, 0.12, 0.20]],
      ],
      rca: [
        [[0.47, 0.44, 0.29], [0.59, 0.50, 0.26], [0.68, 0.45, 0.22]],
        [[0.47, -0.05, 0.27], [0.36, -0.26, 0.24], [0.28, -0.40, 0.20]],
      ],
    };
    const branchMeshes = {};
    for (const id of VESSEL_IDS) {
      branchMeshes[id] = branches[id].map((points) => makeTube(points, 0.014, '#50b5a7', anatomy));
    }

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.enablePan = false;
    controls.minDistance = 3.5;
    controls.maxDistance = 7.2;
    controls.rotateSpeed = 0.55;
    controls.target.set(0, 0.04, 0);

    const raycaster = new THREE.Raycaster();
    raycaster.params.Line.threshold = 0.08;
    const pointer = new THREE.Vector2();
    let downPoint = null;
    const pointerDown = (event) => { downPoint = [event.clientX, event.clientY]; };
    const pointerUp = (event) => {
      if (!downPoint || Math.hypot(event.clientX - downPoint[0], event.clientY - downPoint[1]) > 6) return;
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hits = raycaster.intersectObjects(pickables, false);
      if (hits.length && hits[0].object.userData.vesselId) onSelectRef.current?.(hits[0].object.userData.vesselId);
    };
    const pointerMove = (event) => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      renderer.domElement.style.cursor = raycaster.intersectObjects(pickables, false).length ? 'pointer' : 'grab';
    };
    renderer.domElement.addEventListener('pointerdown', pointerDown);
    renderer.domElement.addEventListener('pointerup', pointerUp);
    renderer.domElement.addEventListener('pointermove', pointerMove);
    renderer.domElement.addEventListener('pointerleave', () => { renderer.domElement.style.cursor = 'grab'; });

    const resize = () => {
      const width = Math.max(1, host.clientWidth);
      const height = Math.max(1, host.clientHeight);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(host);
    resize();

    let animationFrame = 0;
    const animate = () => {
      animationFrame = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    meshRef.current = { vesselMeshes, branchMeshes };
    host.dataset.webgl = 'ready';

    return () => {
      cancelAnimationFrame(animationFrame);
      observer.disconnect();
      controls.dispose();
      renderer.domElement.removeEventListener('pointerdown', pointerDown);
      renderer.domElement.removeEventListener('pointerup', pointerUp);
      renderer.domElement.removeEventListener('pointermove', pointerMove);
      scene.traverse((object) => {
        if (object.geometry) object.geometry.dispose();
        if (object.material) {
          if (Array.isArray(object.material)) object.material.forEach((m) => m.dispose());
          else object.material.dispose();
        }
      });
      renderer.dispose();
      if (renderer.domElement.parentNode === host) host.removeChild(renderer.domElement);
      meshRef.current = {};
    };
  }, []);

  useEffect(() => {
    const { vesselMeshes = {}, branchMeshes = {} } = meshRef.current;
    for (const id of VESSEL_IDS) {
      const score = scoreFor(results, id);
      const color = scoreColor(score);
      const selected = activeVessel === id;
      const targets = [vesselMeshes[id], ...(branchMeshes[id] || [])].filter(Boolean);
      targets.forEach((mesh) => {
        mesh.material.color.copy(color);
        mesh.material.emissive.copy(color);
        mesh.material.emissiveIntensity = selected ? 0.72 : 0.2;
        mesh.material.needsUpdate = true;
      });
    }
  }, [results, activeVessel]);

  return <div className="heart-scene" ref={hostRef} />;
}
