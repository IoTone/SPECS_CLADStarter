/** Shared parametric smooth geometry, in centimeters. No scene or game state. */
export function sphereMesh(r:number, rings=12, sides=20):RenderMesh {
 const v:number[]=[],ix:number[]=[];
 for(let j=0;j<=rings;j++){const a=j*Math.PI/rings;for(let i=0;i<=sides;i++){const b=i*2*Math.PI/sides;const x=Math.sin(a)*Math.cos(b),y=Math.cos(a),z=Math.sin(a)*Math.sin(b);v.push(r*x,r*y,r*z,x,y,z,i/sides,j/rings);}}
 for(let j=0;j<rings;j++)for(let i=0;i<sides;i++){const a=j*(sides+1)+i,b=a+sides+1;ix.push(a,a+1,b,b,a+1,b+1);}
 return mesh(v,ix);
}
export function boxMesh(w:number,h:number,d:number):RenderMesh {
 const v:number[]=[],ix:number[]=[];
 const faces=[[[1,0,0],[w/2,-h/2,-d/2],[w/2,h/2,-d/2],[w/2,h/2,d/2],[w/2,-h/2,d/2]],[[-1,0,0],[-w/2,-h/2,d/2],[-w/2,h/2,d/2],[-w/2,h/2,-d/2],[-w/2,-h/2,-d/2]],[[0,1,0],[-w/2,h/2,-d/2],[-w/2,h/2,d/2],[w/2,h/2,d/2],[w/2,h/2,-d/2]],[[0,-1,0],[-w/2,-h/2,d/2],[-w/2,-h/2,-d/2],[w/2,-h/2,-d/2],[w/2,-h/2,d/2]],[[0,0,1],[-w/2,-h/2,d/2],[w/2,-h/2,d/2],[w/2,h/2,d/2],[-w/2,h/2,d/2]],[[0,0,-1],[w/2,-h/2,-d/2],[-w/2,-h/2,-d/2],[-w/2,h/2,-d/2],[w/2,h/2,-d/2]]];
 for(const f of faces){const k=v.length/8;for(let i=1;i<5;i++)v.push(...f[i],...f[0],i===2||i===3?1:0,i>=3?1:0);ix.push(k,k+1,k+2,k,k+2,k+3);}return mesh(v,ix);
}
export function tubeMesh(points:vec3[],radius:number):RenderMesh {
 const v:number[]=[],ix:number[]=[],sides=12;
 for(let j=0;j<points.length;j++){const p=points[j],next=points[(j+1)%points.length],prev=points[(j+points.length-1)%points.length],t=next.sub(prev).normalize(),up=new vec3(0,1,0),n=t.cross(up).normalize();for(let i=0;i<=sides;i++){const a=i*2*Math.PI/sides,norm=up.uniformScale(Math.cos(a)).add(n.uniformScale(Math.sin(a))),q=p.add(norm.uniformScale(radius));v.push(q.x,q.y,q.z,norm.x,norm.y,norm.z,i/sides,j/points.length);}}
 for(let j=0;j<points.length;j++)for(let i=0;i<sides;i++){const a=j*(sides+1)+i,b=((j+1)%points.length)*(sides+1)+i;ix.push(a,a+1,b,a+1,b+1,b);}return mesh(v,ix);
}
function mesh(v:number[],i:number[]):RenderMesh {const b=new MeshBuilder([{name:'position',components:3},{name:'normal',components:3},{name:'texture0',components:2}]);b.topology=MeshTopology.Triangles;b.indexType=MeshIndexType.UInt16;b.appendVerticesInterleaved(v);b.appendIndices(i);b.updateMesh();return b.getMesh();}
