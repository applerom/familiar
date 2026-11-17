'use client';
import {feedbackEnabled} from '../reader-profile';
import {useEffect,useState} from 'react';
import {translations,type Language} from '../i18n';
export default function Feedback({subject,language,kind='correction'}:{subject:string;language:Language;kind?:string}){
 const t=translations[language];
 const [ready,setReady]=useState(!!(window as any).familiarDeskOpen);
 useEffect(()=>{const loaded=()=>setReady(true);document.addEventListener('familiar-desk-ready',loaded);if((window as any).familiarDeskOpen)loaded();return()=>document.removeEventListener('familiar-desk-ready',loaded)},[]);
 if(!feedbackEnabled())return null;
 const open=()=>document.dispatchEvent(new CustomEvent('familiar-feedback-open',{detail:{kind,subject,person:subject.split(':fact:')[0],screen:'person',...(subject.includes(':fact:')?{finding:subject.split(':fact:')[1]}:{})}}));
 return <button className="link" disabled={!ready} onClick={open}>{kind==='name_person'?t.namePerson:t.knowAction}</button>
}
