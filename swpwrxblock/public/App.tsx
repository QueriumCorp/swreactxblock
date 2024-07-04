import { Canvas } from "@react-three/fiber";
import "./App.css";
import Stage from "./Stage";
import { useEffect } from "react";

interface Props {
  gltfUrl: string;
  swapiUrl: string;
}

const App = (props: Props) => {
  useEffect(() => {
    fetch(props.swapiUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    })
      .then((res) => res.json())
      .then((data) => {
        console.log(data);
      });
  }, [props.swapiUrl]);

  return (
    <Canvas>
      <directionalLight position={[10, 10, 10]} />
      <ambientLight intensity={0.4} />
      <Stage gltfUrl={props.gltfUrl} />
    </Canvas>
  );
};

export default App;
