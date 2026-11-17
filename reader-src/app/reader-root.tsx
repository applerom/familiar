'use client';
import {useEffect,useState} from 'react';
import Family from './family';
import {loadReader,siteURL,type ReaderProfile} from './reader-profile';
export default function ReaderRoot(){
 const [loaded,setLoaded]=useState<{profile:ReaderProfile;data:Record<string,any>}>();const [error,setError]=useState('');
 useEffect(()=>{const url=new URLSearchParams(location.search).get('profile')||siteURL('reader-profile.json');const target=new URL(url,location.href);if(target.origin!==location.origin){setError('Reader profile must use this host');return}loadReader(url).then(setLoaded).catch(e=>setError(String(e)))},[]);
 if(!loaded)return <main className="loading">{error||'…'}</main>;
 return <Family initialData={loaded.data}/>;
}
