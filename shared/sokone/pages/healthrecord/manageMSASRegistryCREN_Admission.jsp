<%@page import="be.mxs.common.model.vo.healthrecord.TransactionVO,
                be.mxs.common.model.vo.healthrecord.ItemVO,
                be.openclinic.pharmacy.Product,
                java.text.DecimalFormat,
                be.openclinic.medical.Problem,
                be.openclinic.medical.Diagnosis,
                be.openclinic.system.Transaction,
                be.openclinic.system.Item,
                be.openclinic.medical.Prescription,
                java.util.*" %>
<%@ page import="java.sql.Date" %>
<%@ page import="be.openclinic.medical.PaperPrescription" %>
<%@include file="/includes/validateUser.jsp"%>
<%@page errorPage="/includes/error.jsp"%>
<%
	String accessright="msas.registry.cren";
%>
<%=checkPermission(accessright,"select",activeUser)%>
     <%-- 
    <form name="transactionForm" id="transactionForm" method="POST" action='<c:url value="/healthrecord/updateTransaction.do"/>?ts=<%=getTs()%>'>
    --%>
     <!--
    <bean:define id="transaction" name="be.mxs.webapp.wl.session.SessionContainerFactory.WO_SESSION_CONTAINER" property="currentTransactionVO"/>
	-->
	<%//=checkPrestationToday(activePatient.personid,false,activeUser,(TransactionVO)transaction)%>
   
    <%//=ScreenHelper.writeDefaultHiddenInput((TransactionVO)transaction, "ITEM_TYPE_CONTEXT_DEPARTMENT") %>
    <%//=ScreenHelper.writeDefaultHiddenInput((TransactionVO)transaction, "ITEM_TYPE_CONTEXT_CONTEXT") %>
    
    <%//=writeHistoryFunctions(((TransactionVO)transaction).getTransactionType(),sWebLanguage)%>
    <%//=contextHeader(request,sWebLanguage)%>
    
    <table class="list" width="100%" cellspacing="1">
        <%-- DATE --%>
   
		<tr>
		   	<td class='admin'><%=getTran(request,"web","mothersname",sWebLanguage) %></td>
		   	<td class='admin2'>
		   						<%=SH.writeDefaultTextInput(session, (TransactionVO)transaction, "ITEM_TYPE_CREN_MOTHERSNAME", 50) %>
		   						<br/><br/>
		   						<%=getTran(request,"web","adressphone",sWebLanguage) %>
		   						<%=SH.writeDefaultTextInput(session, (TransactionVO)transaction, "ITEM_TYPE_CREN_MOTHERADRESS", 37) %>
		   	</td>
		   	<td class='admin'><%=getTran(request,"web","admissiontype",sWebLanguage) %></td>
		   	<td class='admin2'>
		   		<%=SH.writeDefaultSelect(request, (TransactionVO)transaction, "ITEM_TYPE_CREN_ADMISSIONTYPE", "msas.cre.admissiontype",sWebLanguage, "onchange='checkAdmission()'") %> <span id='admissionreason' style='display: none'><%=SH.writeDefaultSelect(request, (TransactionVO)transaction, "ITEM_TYPE_MSAS_CREN_ADMISSIONREASON","msas.cren.admissionreason", sWebLanguage, "") %></span><BR/>
		   		<%=SH.writeDefaultCheckBoxes((TransactionVO)transaction, request, "msas.uren.communityreferral", "ITEM_TYPE_MSAS_UREN_COMMUNITYREFERRAL", sWebLanguage, false) %>
		   	</td>
		   	<script>
		   		function checkAdmission(){
		   			if(document.getElementById("ITEM_TYPE_CREN_ADMISSIONTYPE").value=='1'){
		   				document.getElementById('admissionreason').style.display='';
		   			}
		   			else{
		   				document.getElementById('admissionreason').style.display='none';
		   				document.getElementById("ITEM_TYPE_MSAS_CREN_ADMISSIONREASON").selectedIndex=0;
		   			}
		   		}
		   		checkAdmission();
		   	</script>
		</tr>
		<tr>
		   	<td class='admin'><%=getTran(request,"web","internaltransferfrom",sWebLanguage) %></td>
		   	<td class='admin2'>
		   		<%=SH.writeDefaultRadioButtons((TransactionVO)transaction, request, "msas.transferfrom", "ITEM_TYPE_CREN_TRANSFERFROM", sWebLanguage, false, "", "") %>
		   		&nbsp;&nbsp;<%=getTran(request,"web","name",sWebLanguage) %>:
		   		<%=SH.writeDefaultTextInput(session, (TransactionVO)transaction, "ITEM_TYPE_CREN_FROMNAME", 30) %>
		   	</td>
		   	<td class='admin'><%=getTran(request,"web","masnumber",sWebLanguage) %></td>
		   	<td class='admin2'><%=SH.writeDefaultTextInput(session, (TransactionVO)transaction, "ITEM_TYPE_CREN_MAS", 20) %></td>
		</tr>
		<tr>
		   	<td class='admin'><%=getTran(request,"web","complicationtype",sWebLanguage) %></td>
		   	<td class='admin2' ><%=SH.writeDefaultTextArea(session, (TransactionVO)transaction, "ITEM_TYPE_CREN_COMPLICATION", 50,1) %></td>
				
			<td class='admin' ><%=getTran(request,"web","site",sWebLanguage) %></td>
			        	<td class='admin2' ><%=SH.writeDefaultRadioButtons((TransactionVO)transaction, request,"msas.site", "!ITEM_TYPE_MSAS_CONS_SITE", sWebLanguage, true, "", "")%></td>
		
		
		</tr>
        <tr class='admin'><td colspan='4'><%=getTran(request,"web","anthropometry",sWebLanguage) %></td></tr>
		<tr>
			<td class='admin2' colspan='4'><%writeVitalSigns(pageContext); %></td>
		</tr>	
		<tr>
		   	<td class='admin'><%=getTran(request,"web","observations",sWebLanguage) %></td>
		   	<td class='admin2'><%=SH.writeDefaultTextArea(session, (TransactionVO)transaction, "ITEM_TYPE_CREN_OBSERVATIONS", 50, 1) %></td>
		   	<td class='admin'><%=getTran(request,"web","oedema",sWebLanguage) %></td>
			<td class='admin2'><%= SH.writeDefaultRadioButtons((TransactionVO)transaction, request, "yesno", "ITEM_TYPE_CREN_OEDEMA", sWebLanguage, false,"","") %></td>
		</tr>
		
		<!-- Ajout des items (ITEM_TYPE_MSAS_CONS_IRA) dans le registre CREN -->
		<tr>
		   	<td class='admin'><%=getTran(request,"web", "consultation.ira", sWebLanguage)%></td>
		   	<td class='admin2' colspan="4"><%=SH.writeDefaultCheckBoxes((TransactionVO)transaction, request, "msas.ira", "ITEM_TYPE_MSAS_CONS_IRA",sWebLanguage, false) %></td>
		</tr>
		
		<!-- FIN Ajout des items (ITEM_TYPE_MSAS_CONS_IRA) dans le registre CREN -->
		        <tr>
        	<td colspan='2'><%ScreenHelper.setIncludePage(customerInclude("healthrecord/diagnosesEncoding.jsp"),pageContext);%></td>
        </tr>
    </table>
    <table width="100%" class="list" cellspacing="1">
        <tr class="admin">
            <td align="center"><a href="javascript:openPopup('medical/managePrescriptionsPopup.jsp&amp;skipEmpty=1',900,400,'medication');void(0);"><%=getTran(request,"Web.Occup","medwan.healthrecord.medication",sWebLanguage)%></a></td>
        </tr>
        <tr>
            <td>
        <%
            //--- DISPLAY ACTIVE PRESCRIPTIONS (of activePatient) ---------------------------------
            // compose query
            Vector vActivePrescriptions = Prescription.findActive(activePatient.personid,activeUser.userid,"","","","","","");

            StringBuffer prescriptions = new StringBuffer();
            Vector idsVector = be.mxs.common.util.system.PrescriptionRows.getActivePrescriptionsFromRs(prescriptions, vActivePrescriptions , sWebLanguage, sCONTEXTPATH,
                    be.mxs.common.util.system.PrescriptionRows.UNIT_LABEL_PLURAL, false, true);
            int foundPrescrCount = idsVector.size();

            if(foundPrescrCount > 0){
                %>
                    <table width="100%" cellspacing="0" cellpadding="0" class="list">
                        <%-- header --%>
                        <tr class="admin">
                            <td width="22" nowrap>&nbsp;</td>
                            <td width="30%"><%=getTran(request,"Web","product",sWebLanguage)%></td>
                            <td width="15%"><%=getTran(request,"Web","begindate",sWebLanguage)%></td>
                            <td width="15%"><%=getTran(request,"Web","enddate",sWebLanguage)%></td>
                            <td width="40%"><%=getTran(request,"Web","prescriptionrule",sWebLanguage)%></td>
                        </tr>

                        <tbody class="hand"><%=prescriptions%></tbody>
                    </table>
                <%
            }
            else{
                // no records found
                %><%=getTran(request,"web","noactiveprescriptionsfound",sWebLanguage)%><br><%
            }
            %>
            </td>
        </tr>
        <tr class="admin">
            <td align="center"><%=getTran(request,"curative","medication.paperprescriptions",sWebLanguage)%> (<%=ScreenHelper.stdDateFormat.format(((TransactionVO)transaction).getUpdateTime())%>)</td>
        </tr>
        <%
            Vector paperprescriptions = PaperPrescription.find(activePatient.personid,"",ScreenHelper.stdDateFormat.format(((TransactionVO)transaction).getUpdateTime()),ScreenHelper.stdDateFormat.format(((TransactionVO)transaction).getUpdateTime()),"","DESC");
            if(paperprescriptions.size()>0){
                out.print("<tr><td><table width='100%'>");
                String l="";
                for(int n=0;n<paperprescriptions.size();n++){
                    if(l.length()==0){
                        l="1";
                    }
                    else{
                        l="";
                    }
                    PaperPrescription paperPrescription = (PaperPrescription)paperprescriptions.elementAt(n);
                    out.println("<tr class='list"+l+"' id='pp"+paperPrescription.getUid()+"'><td valign='top' width='90px'><img src='_img/icons/icon_delete.png' onclick='deletepaperprescription(\""+paperPrescription.getUid()+"\");'/> <b>"+ScreenHelper.stdDateFormat.format(paperPrescription.getBegin())+"</b></td><td><i>");
                    Vector products =paperPrescription.getProducts();
                    for(int i=0;i<products.size();i++){
                        out.print(products.elementAt(i)+"<br/>");
                    }
                    out.println("</i></td></tr>");
                }
                out.print("</table></td></tr>");
            }
        %>
        <tr>
            <td><a href="javascript:openPopup('medical/managePrescriptionForm.jsp&amp;skipEmpty=1',650,430,'medication');void(0);"><%=getTran(request,"web","medicationpaperprescription",sWebLanguage)%></a></td>
        </tr>
    </table>            
	<%-- BUTTONS --%>
	<%//=ScreenHelper.alignButtonsStart()%>
	    <%//=getButtonsHtml(request,activeUser,activePatient,accessright,sWebLanguage)%>
	<%//=ScreenHelper.alignButtonsStop()%>
	
    <%=ScreenHelper.contextFooter(request)%>
  <%--  </form> --%>

<script>
  function searchEncounter(){
    openPopup("/_common/search/searchEncounter.jsp&ts=<%=getTs()%>&VarCode=encounteruid&VarText=&FindEncounterPatient=<%=activePatient.personid%>");
  }
  
  if( document.getElementById('encounteruid').value=="" <%=((TransactionVO)transaction).getItemValue("be.mxs.common.model.vo.healthrecord.IConstants.ITEM_TYPE_REFERRAL_SOURCESITE").length()==0 && request.getParameter("nobuttons")==null?"":" && 1==0"%>){
  	alertDialogDirectText('<%=getTranNoLink("web","no.encounter.linked",sWebLanguage)%>');
  	searchEncounter();
  }	

  function searchUser(managerUidField,managerNameField){
	  openPopup("/_common/search/searchUser.jsp&ts=<%=getTs()%>&ReturnUserID="+managerUidField+"&ReturnName="+managerNameField+"&displayImmatNew=no&FindServiceID=<%=be.openclinic.core.db.Config.getConfigString("CCBRTEyeRegistryService")%>",650,600);
    document.getElementById(diagnosisUserName).focus();
  }
  

</script>
    
<%//=writeJSButtons("transactionForm","saveButton")%>