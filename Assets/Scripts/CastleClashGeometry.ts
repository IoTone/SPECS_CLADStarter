/** Parametric, destructible miniature mesh backend. Dimensions are actual cm. */
export type Color=[number,number,number,number];
export type Block=[number,number,number,number,number,number,Color];
export function castleMesh(blocks:Block[]):RenderMesh{
 const b=new MeshBuilder([{name:'position',components:3},{name:'normal',components:3,normalized:true},{name:'color',components:4}]);b.topology=MeshTopology.Triangles;b.indexType=MeshIndexType.UInt16;
 const v:number[]=[],ix:number[]=[];
 for(const [x,y,z,w,h,d,c] of blocks){const a=x-w/2,A=x+w/2,e=y-h/2,E=y+h/2,f=z-d/2,F=z+d/2;
 const faces=[[[A,e,f],[A,E,f],[A,E,F],[A,e,F],[1,0,0]],[[a,e,F],[a,E,F],[a,E,f],[a,e,f],[-1,0,0]],[[a,E,f],[a,E,F],[A,E,F],[A,E,f],[0,1,0]],[[a,e,F],[a,e,f],[A,e,f],[A,e,F],[0,-1,0]],[[a,e,F],[A,e,F],[A,E,F],[a,E,F],[0,0,1]],[[A,e,f],[a,e,f],[a,E,f],[A,E,f],[0,0,-1]]];
 for(const face of faces){const base=v.length/10;const shade=face[4][1]>0?1:face[4][2]!==0?0.86:0.72;for(let i=0;i<4;i++)v.push(...face[i],...face[4],c[0]*shade,c[1]*shade,c[2]*shade,c[3]);ix.push(base,base+1,base+2,base,base+2,base+3);}}
 b.appendVerticesInterleaved(v);b.appendIndices(ix);b.updateMesh();return b.getMesh();
}
export function meshObject(parent:SceneObject,name:string,blocks:Block[],material:Material){const o=global.scene.createSceneObject(name);o.setParent(parent);const r=o.createComponent('Component.RenderMeshVisual') as RenderMeshVisual;r.mesh=castleMesh(blocks);r.mainMaterial=material;return o;}
