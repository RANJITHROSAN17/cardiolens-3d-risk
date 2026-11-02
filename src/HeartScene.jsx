import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

import { VESSEL_IDS, FALLBACK_PATHS, scoreColor, vesselCards, tryCreateRenderer } from './heart-visualization.js';
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

export default function HeartScene({ results, activeVessel, onVesselSelect, onModeChange, palette = 'viridis' }) {
  const [webglFailed, setWebglFailed] = useState(false);
  const cards = vesselCards(results);
  const hostRef = useRef(null);
  const meshRef = useRef({});
  const onSelectRef = useRef(onVesselSelect);

  useEffect(() => { onSelectRef.current = onVesselSelect; }, [onVesselSelect]);
  useEffect(() => { onModeChange?.(webglFailed ? 'fallback' : 'webgl'); }, [webglFailed, onModeChange]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || webglFailed) return undefined;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 40);
    camera.position.set(0, 0.08, 5.25);

    const renderer = tryCreateRenderer(() => new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' }));
    if (!renderer) { setWebglFailed(true); return undefined; }
    const contextLost = (event) => { event.preventDefault(); setWebglFailed(true); };
    renderer.domElement.addEventListener('webglcontextlost', contextLost);
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
    const pointerLeave = () => { renderer.domElement.style.cursor = 'grab'; };
    renderer.domElement.addEventListener('pointerleave', pointerLeave);

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
      renderer.domElement.removeEventListener('webglcontextlost', contextLost);
      renderer.domElement.removeEventListener('pointerleave', pointerLeave);
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
  }, [webglFailed]);

  useEffect(() => {
    const { vesselMeshes = {}, branchMeshes = {} } = meshRef.current;
    for (const { id, score } of vesselCards(results)) {
      const color = new THREE.Color(scoreColor(score, palette));
      const selected = activeVessel === id;
      const targets = [vesselMeshes[id], ...(branchMeshes[id] || [])].filter(Boolean);
      targets.forEach((mesh) => {
        mesh.material.color.copy(color);
        mesh.material.emissive.copy(color);
        mesh.material.emissiveIntensity = selected ? 0.72 : 0.2;
        mesh.material.needsUpdate = true;
      });
    }
  }, [results, activeVessel, palette, webglFailed]);

  return <div className="heart-scene" data-view={webglFailed ? 'fallback' : 'webgl'}>
    {!webglFailed && <div className="heart-webgl" ref={hostRef} />}
    {webglFailed && <div className="heart-fallback">
      <p role="status">3D unavailable — showing a selectable 2D schematic.</p>
      <svg viewBox="0 0 320 280" aria-hidden="true" focusable="false">
        <path d="M160 56 C110 4 30 34 34 115 C38 183 118 231 160 258 C202 231 282 183 286 115 C290 34 210 4 160 56Z" fill="#f5e4e9" stroke="#82465a" strokeWidth="2" />
        {cards.map(card => <g key={card.id}>
          <path d={FALLBACK_PATHS[card.id]} fill="none" stroke="#18343e" strokeWidth={activeVessel === card.id ? 17 : 12} strokeLinecap="round" />
          <path d={FALLBACK_PATHS[card.id]} fill="none" stroke={scoreColor(card.score, palette)} strokeWidth="8" strokeLinecap="round" />
        </g>)}
        <g fill="#18343e" fontSize="15" fontWeight="bold"><text x="170" y="228">LAD</text><text x="63" y="177">LCX</text><text x="235" y="210">RCA</text></g>
      </svg>
    </div>}
    <div className="scene-vessel-badges" role="group" aria-label="Select schematic vessel; whole-vessel scores, not clinical probabilities">
      {cards.map(card => <button type="button" key={card.id} aria-pressed={activeVessel === card.id}
        onClick={() => onVesselSelect?.(card.id)}>
        <span className="scene-vessel-swatch" style={{ background: scoreColor(card.score, palette) }} aria-hidden="true" />
        <strong>{card.label}</strong><span>{card.text}</span>{activeVessel === card.id && <span className="scene-selected">Selected</span>}
      </button>)}
    </div>
  </div>;
}
