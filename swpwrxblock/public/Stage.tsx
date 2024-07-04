import { useThree } from "@react-three/fiber";
import Model from "./models/foxy/model";
import * as THREE from "three";

interface Props {
  gltfUrl: string;
}

const Stage = (props: Props) => {
  let target, viewer, zoom;

  // Full Body
  target = { x: 0, y: 0.05, z: 0 };
  viewer = { x: 0, y: 0.025, z: 0.18 };
  zoom = 2.1;

  useThree((state) => {
    state.camera?.position.set(viewer.x, viewer.y, viewer.z);
    state.camera?.lookAt(new THREE.Vector3(target.x, target.y, target.z));
    state.camera.zoom = zoom;
    state.camera.up = new THREE.Vector3(0, 1, 0);
    state.camera.updateProjectionMatrix();
  });
  return (
    <mesh>
      <Model emote={"celebrate:09"} gltfUrl={props.gltfUrl} />
    </mesh>
  );
};

export default Stage;
