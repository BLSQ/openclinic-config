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
	String accessright="msas.laboratory";
%>
<%=checkPermission(accessright,"select",activeUser)%>
<form name="transactionForm" id="transactionForm" method="POST" action='<c:url value="/healthrecord/updateTransaction.do"/>?ts=<%=getTs()%>'>
    <bean:define id="transaction" name="be.mxs.webapp.wl.session.SessionContainerFactory.WO_SESSION_CONTAINER" property="currentTransactionVO"/>
	<%=checkPrestationToday(activePatient.personid,false,activeUser,(TransactionVO)transaction)%>
   
    <input type="hidden" id="transactionId" name="currentTransactionVO.<TransactionVO[hashCode=<bean:write name="transaction" scope="page" property="transactionId"/>]>.transactionId" value="<bean:write name="transaction" scope="page" property="transactionId"/>"/>
    <input type="hidden" id="serverId" name="currentTransactionVO.<TransactionVO[hashCode=<bean:write name="transaction" scope="page" property="transactionId"/>]>.serverId" value="<bean:write name="transaction" scope="page" property="serverId"/>"/>
    <input type="hidden" id="transactionType" name="currentTransactionVO.<TransactionVO[hashCode=<bean:write name="transaction" scope="page" property="transactionId"/>]>.transactionType" value="<bean:write name="transaction" scope="page" property="transactionType"/>"/>
    <input type="hidden" readonly name="be.mxs.healthrecord.updateTransaction.actionForwardKey" value="/main.do?Page=curative/index.jsp&ts=<%=getTs()%>"/>
    <%=ScreenHelper.writeDefaultHiddenInput((TransactionVO)transaction, "ITEM_TYPE_CONTEXT_DEPARTMENT") %>
    <%=ScreenHelper.writeDefaultHiddenInput((TransactionVO)transaction, "ITEM_TYPE_CONTEXT_CONTEXT") %>
    
    <%=writeHistoryFunctions(((TransactionVO)transaction).getTransactionType(),sWebLanguage)%>
    <%=contextHeader(request,sWebLanguage)%>
    
    <table class="list" width="100%" cellspacing="1">
        <%-- DATE --%>
        <tr>
            <td class="admin" width="<%=sTDAdminWidth%>" colspan="4">
                <a href="javascript:openHistoryPopup();" title="<%=getTranNoLink("Web.Occup","History",sWebLanguage)%>">...</a>&nbsp;
                <%=getTran(request,"Web.Occup","medwan.common.date",sWebLanguage)%>
                <input type="text" class="text" size="12" maxLength="10" name="currentTransactionVO.<TransactionVO[hashCode=<bean:write name="transaction" scope="page" property="transactionId"/>]>.updateTime" value="<mxs:propertyAccessorI18N name="transaction" scope="page" property="updateTime" formatType="date"/>" id="trandate" OnBlur='checkDate(this)'>
                <script>writeTranDate();</script>
            </td>
        </tr>
        <tr class='admin'><td colspan='4'><%=getTran(request,"web","labo",sWebLanguage) %></td></tr> 
  
		 <tr>
          	<td class='admin'><%=getTran(request,"web","profession",sWebLanguage)%>&nbsp;</td>
			<td class='admin2'><%=SH.writeDefaultTextInput(session, (TransactionVO)transaction, "ITEM_TYPE_MSAS_LABORATY_PROFESSION", 30) %></td>
    		<td class='admin'><%=getTran(request,"web","structureprovenance",sWebLanguage)%>&nbsp;</td>
			<td class='admin2'><%=SH.writeDefaultTextInput(session, (TransactionVO)transaction, "ITEM_TYPE_MSAS_LABORATY_STRUCTURE_PROVENANCE", 30) %></td>
        </tr> 
         <tr>
          	<td class="admin"><%=getTran(request,"web", "motif", sWebLanguage)%></td>
            <td class="admin2" colspan="4"><%=ScreenHelper.writeDefaultCheckBoxes((TransactionVO)transaction, request, "msas.motif", "ITEM_TYPE_MSAS_LABORATY_MOTIF", sWebLanguage, true) %> </td> 
         	
         </tr> 
          <tr>
          	<td class="admin"><%=getTran(request,"web", "resultat", sWebLanguage)%></td>
            <td class="admin2"><%=ScreenHelper.writeDefaultRadioButtons((TransactionVO)transaction, request, "msas.resultat",  "ITEM_TYPE_MSAS_LABORATY_RESULTAT", sWebLanguage, true, "", " ") %> </td> 
         	<td class="admin"><%=getTran(request,"web", "verification", sWebLanguage)%></td>
            <td class="admin2">
            	<%=ScreenHelper.writeDefaultRadioButtons((TransactionVO)transaction, request, "msas.verification",  "ITEM_TYPE_MSAS_LABORATY_VERIFICATION", sWebLanguage, true, "", " ") %>
            </td>
         </tr>        
          <tr>
          <td class="admin" > <%=getTran(request,"web","resultatrendue",sWebLanguage)%></td>
            <td class="admin2" colspan="4"> <%=SH.writeDefaultTextArea(session, (TransactionVO)transaction, "ITEM_TYPE_MSAS_LABORATY_RESULTAT_RENDUE",40, 2)%>
            &nbsp;&nbsp;&nbsp;&nbsp; 
            <%=getTran(request,"web","daterendue",sWebLanguage) %> &nbsp;&nbsp;
            <%=SH.writeDefaultDateInput(session, (TransactionVO)transaction, "ITEM_TYPE_MSAS_LABORATY_DATE_RESULTAT", sWebLanguage, sCONTEXTPATH) %></td>
        	
        </tr>
         <tr>
         	<td class="admin" > <%=getTran(request,"web","observation",sWebLanguage)%></td>
            <td class="admin2" colspan="4"> <%=SH.writeDefaultTextArea(session, (TransactionVO)transaction, "ITEM_TYPE_MSAS_LABORATY_OBSERVATION",40, 2)%></td>
        	
        </tr>
        
        
        
    </table>            
	<%-- BUTTONS --%>
	<%=ScreenHelper.alignButtonsStart()%>
	    <%=getButtonsHtml(request,activeUser,activePatient,accessright,sWebLanguage)%>
	<%=ScreenHelper.alignButtonsStop()%>
	
    <%=ScreenHelper.contextFooter(request)%>
</form>

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

  function submitForm(){
    transactionForm.saveButton.disabled = true;
    <%
        SessionContainerWO sessionContainerWO = (SessionContainerWO)SessionContainerFactory.getInstance().getSessionContainerWO(request,SessionContainerWO.class.getName());
        out.print(takeOverTransaction(sessionContainerWO,activeUser,"document.transactionForm.submit();"));
    %>
  }
</script>
    
<%=writeJSButtons("transactionForm","saveButton")%>