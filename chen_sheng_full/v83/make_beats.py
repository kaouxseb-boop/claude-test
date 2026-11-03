import json,pathlib
P=pathlib.Path(__file__).resolve().parent
# Absolute starts grounded in the repaired ASR. Later anchors are updated after ASR completes.
rows=[
(0,'900 คน เขย่าจักรวรรดิ','daze',None,'intro'),
(6.24,'เฉินเซิ่ง คนธรรมดา','daze',None,'chen'),
(13.22,'จุดจบที่คาดไม่ถึง','xiachengfu',None,'death'),
(23.32,'เมื่อกว่า 2,200 ปีก่อน','xianyang',None,'qin'),
(31.52,'เริ่มที่ต้าเจ๋อเซียง','daze',None,'chen'),
(34.50,'จุดหมายอยู่ทางเหนือ','yuyang','daze','plan'),
(41.46,'ฝนหยุดขบวนทหาร','daze',None,'rain'),
(54.48,'เฉินเซิ่ง และอู๋กว่าง','daze',None,'chen'),
(69.44,'ลุกขึ้นสู้ที่ต้าเจ๋อเซียง','daze',None,'revolt'),
(88.20,'ชัยชนะแรก เมืองฉี','qi','daze','capture'),
(104.90,'ขยายกำลังสู่เมืองจื้อ','zhi','qi','capture'),
(109.12,'ยึดเมืองจ้าน','zan','zhi','capture'),
(112.94,'เมืองขู่ และเจ้อ','zhe','ku','capture'),
(118.94,'กองกำลังถึงเฉียว','qiao','zhe','capture'),
(127.08,'กองทัพรุกเมืองเฉิน','chen','qiao','capture'),
(146.18,'ตั้งรัฐจางฉู่','chen',None,'chen'),
(162.46,'อู๋กว่างมุ่งสิงหยาง','xingyang','chen','move'),
(171.60,'หลี่โหยวตั้งรับ','xingyang',None,'siege'),
(190.36,'โจวเหวินบุกตะวันตก','hangu','chen','move'),
(205.66,'กองทัพถึงเขตซี','xi','hangu','move'),
(214.62,'จางหานระดมกำลัง','lishan',None,'qin'),
(233.68,'ฉินโต้กลับโจวเหวิน','xi','lishan','qin_attack'),
(237.80,'ถอยสู่เฉาหยาง','caoyang','xi','retreat'),
(242.28,'พ่ายที่เหมี่ยนฉือ','mianchi','caoyang','retreat'),
(258.52,'กบฏแตกคอกันที่สิงหยาง','xingyang',None,'siege'),
(288.0,'รบที่อ๋าวชาง','aocang','xingyang','battle'),
(300.1,'ฉินตีสิงหยาง','xingyang','aocang','qin_attack'),
(303.88,'กองทัพฉินมุ่งเมืองเฉิน','chen','xingyang','qin_attack'),
(318.38,'เฉินเซิ่งหนีออกจากเมือง','xiachengfu','chen','retreat'),
(333.0,'ถูกคนขับรถม้าสังหาร','xiachengfu',None,'death'),
(353.0,'ไฟกบฏยังไม่ดับ','daze',None,'rebels'),
(356.44,'ลวี่เฉินยึดเมืองเฉินคืน','chen',None,'capture'),
(363.0,'กบฏลุกลามทั่วแผ่นดิน','chen',None,'rebels'),
(367.96,'เซี่ยงอวี่ที่จวี้ลู่','julu',None,'battle'),
(372.44,'หลิวปังเข้าสู่เสียนหยาง','xianyang','wuguan','capture'),
(378.48,'จักรวรรดิฉินล่มสลาย','xianyang',None,'rebels'),
(383.84,'ชื่อของเฉินเซิ่งในประวัติศาสตร์','daze',None,'chen')]
def save(rows):
 beats=[];controlled=[]
 for i,(t,title,dest,origin,kind) in enumerate(rows):
  end=rows[i+1][0] if i+1<len(rows) else 402.12
  b=dict(start=t,end=end,title=title,dest=dest,origin=origin,kind=kind,controlled=controlled.copy(),show=[dest]+([origin] if origin else []))
  b['note']={'capture':'กองกำลังกบฏรุกยึดเมือง','qin_attack':'กองทัพฉินโต้กลับ','siege':'การล้อมเมือง • ยังยึดไม่ได้','retreat':'กองกำลังกบฏถอยทัพ','plan':'เส้นทางที่ถูกสั่งให้ไป • ยังเดินทางไม่ถึง','rain':'ฝนหนัก • ขบวนหยุดเดินทาง','death':'จุดเกิดเหตุโดยประมาณ','chen':'จากทหารเกณฑ์สู่ผู้นำกบฏ'}.get(kind,'')
  if kind.startswith('qin'):
   b['side']='qin'
   if kind=='qin_attack' or dest=='lishan':b['portrait']='zhang'
  elif kind=='chen':b['portrait']='chen'
  if kind in ['capture','qin_attack','revolt']:b['capture']=True
  if dest=='qi' and kind=='capture':b['capture_at']=95.12-t
  if kind=='death':b['portrait']='chen'
  if kind=='intro':b['show']=['daze','xianyang'];b['zoom']=6
  if kind=='plan':b['planned']=True
  beats.append(b)
  if kind in ['capture','revolt'] and dest not in controlled:controlled.append(dest)
  if kind=='qin_attack' and dest in controlled:controlled.remove(dest)
 (P/'beats.json').write_text(json.dumps(beats,ensure_ascii=False,indent=2))
 return beats
if __name__=='__main__':save(rows)
